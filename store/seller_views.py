# seller_views.py

import logging
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db import transaction

from .models import (
    Product,
    ProductDetails,
    ProductImage,
    ProductListing,
    Category,
    Tag,
)


logger = logging.getLogger(__name__)


@login_required
def seller_add_product(request):

    seller_profile = getattr(
        request.user,
        "seller_profile",
        None
    )

    if not seller_profile:
        raise PermissionDenied


    if request.method == "POST":

        title = request.POST.get("title")
        price_raw = request.POST.get("price")
        stock = request.POST.get("stock") or 0
        category_id = request.POST.get("category")


        if not title or not price_raw or not category_id:
            return HttpResponse(
                "Заполните обязательные поля",
                status=400
            )


        try:
            price = Decimal(
                str(price_raw).replace(",", ".")
            )

        except InvalidOperation:
            return HttpResponse(
                "Некорректная цена",
                status=400
            )


        category = get_object_or_404(
            Category,
            id=category_id
        )


        main_image = request.FILES.get(
            "product_image"
        )

        gallery = request.FILES.getlist(
            "gallery_images"
        )


        tags = request.POST.getlist(
            "selected_tags"
        )


        try:

            with transaction.atomic():

                # 1. товар
                product = Product.objects.create(
                    name=title,
                    category=category,
                    image=main_image,
                    owner=request.user,
                    is_active=False,
                )


                # 2. теги
                if tags:
                    product.tags.set(tags)


                # 3. детали
                ProductDetails.objects.create(
                    product=product,
                    price=price,
                    stock=stock,
                )


                # 4. объявление продавца
                ProductListing.objects.create(
                    product=product,
                    owner=request.user,
                    seller_type="seller",
                    moderation_status="pending",
                    is_active=False,
                )


                # 5. галерея
                for image in gallery[:10]:

                    ProductImage.objects.create(
                        product=product,
                        image=image
                    )


            logger.info(
                f"Продавец {request.user.username} "
                f"создал товар {product.name}"
            )


            return redirect(
                "seller_dashboard"
            )


        except Exception as e:

            logger.error(
                str(e),
                exc_info=True
            )

            return HttpResponse(
                "Ошибка создания товара",
                status=500
            )


    return render(
        request,
        "store/seller/add.html",
        {
            "categories": Category.objects.all(),
            "tags": Tag.objects.all(),
        }
    )

@login_required
def seller_dashboard(request):

    seller = getattr(
        request.user,
        "seller_profile",
        None
    )

    if not seller:
        raise PermissionDenied


    listings = (
        ProductListing.objects
        .filter(
            owner=request.user,
            seller_type="seller"
        )
        .select_related(
            "product",
            "product__details",
            "product__category",
        )
    )


    return render(
        request,
        "store/seller/dashboard.html",
        {
            "listings": listings,
            "seller": seller,
        }
    )
    

@login_required
def seller_products(request):

    listings = ProductListing.objects.filter(
        owner=request.user,
        seller_type="seller"
    ).select_related(
        "product",
        "product__details",
        "product__category",
    ).prefetch_related(
        "product__images"
    )


    return render(
        request,
        "store/seller/products.html",
        {
            "listings": listings
        }
    )
    
    
@login_required
def seller_edit_product(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id,
        owner=request.user,
    )


    listing = get_object_or_404(
        ProductListing,
        product=product,
        owner=request.user,
        seller_type="seller",
    )


    if request.method == "POST":

        title = request.POST.get("title")
        price_raw = request.POST.get("price")
        stock = request.POST.get("stock") or 0
        category_id = request.POST.get("category")


        if not title or not price_raw or not category_id:
            return HttpResponse(
                "Заполните обязательные поля",
                status=400
            )


        try:

            price = Decimal(
                str(price_raw)
                .replace(",", ".")
            )

        except InvalidOperation:

            return HttpResponse(
                "Некорректная цена",
                status=400
            )



        category = get_object_or_404(
            Category,
            id=category_id
        )



        with transaction.atomic():


            # товар

            product.name = title
            product.category = category


            new_image = request.FILES.get(
                "product_image"
            )

            if new_image:

                product.image = new_image


            product.is_active = False

            product.save()



            # детали

            details = get_object_or_404(
                ProductDetails,
                product=product
            )

            details.price = price
            details.stock = stock
            details.save()



            # теги

            tags = request.POST.getlist(
                "selected_tags"
            )

            product.tags.set(tags)



            # отправляем заново на проверку

            listing.moderation_status = "pending"
            listing.moderation_comment = ""
            listing.is_active = False

            listing.save()



            # новые фото

            gallery = request.FILES.getlist(
                "gallery_images"
            )


            for image in gallery[:10]:

                ProductImage.objects.create(
                    product=product,
                    image=image
                )



        return redirect(
            "seller_products"
        )



    return render(
        request,
        "store/seller/edit.html",
        {
            "product": product,
            "listing": listing,
            "categories": Category.objects.all(),
            "tags": Tag.objects.all(),
        }
    )