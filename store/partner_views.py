from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from .models import OrderItem, PartnerProfile, Product, ProductDetails, ProductImage, Category, Tag

from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import Coalesce
from .models import (
    OrderItem,
    Product,
    ProductListing,
    ProductDetails,
    ProductImage,
    Category,
    Tag,
)


@login_required
def partner_dashboard(request):
    profile = getattr(request.user, "partner_profile", None)

    if not profile or not profile.is_active:
        raise PermissionDenied(
            "У вас нет доступа к кабинету партнёра."
        )

    context = {
        "partner": profile,
    }

    return render(
        request,
        "store/partner/dashboard.html",
        context
    )

@login_required
def partner_products(request):
    profile = getattr(request.user, "partner_profile", None)

    if not profile or not profile.is_active:
        raise PermissionDenied(
            "У вас нет доступа к кабинету партнёра."
        )

    products = Product.objects.filter(
        listing__owner=request.user
    ).select_related(
        "details",
        "listing",
        "category",
    )

    context = {
        "partner": profile,
        "products": products,
    }

    return render(
        request,
        "store/partner/products.html",
        context
    )


@login_required
def partner_orders(request):
    profile = getattr(request.user, "partner_profile", None)

    if not profile or not profile.is_active:
        raise PermissionDenied(
            "У вас нет доступа к кабинету партнёра."
        )

    order_items = (
        OrderItem.objects
        .filter(product__listing__owner=request.user)
        .select_related("order", "product")
        .order_by("-order__id")
    )

    return render(
        request,
        "store/partner/orders.html",
        {
            "partner": profile,
            "order_items": order_items,
        }
    )

    
    
@login_required
def partner_analytics(request):
    profile = getattr(request.user, "partner_profile", None)

    if not profile or not profile.is_active:
        raise PermissionDenied(
            "У вас нет доступа к аналитике партнёра."
        )

    products = Product.objects.filter(
        listing__owner=request.user
    )

    order_items = OrderItem.objects.filter(
        product__listing__owner=request.user
    )

    total_products = products.count()

    total_sales = (
        order_items.aggregate(
            total=Coalesce(Sum("quantity"), 0)
        )["total"]
    )

    total_revenue = (
        order_items.aggregate(
            total=Coalesce(
                Sum(F("price") * F("quantity")),
                0,
                output_field=DecimalField()
            )
        )["total"]
    )

    total_orders = (
        order_items
        .values("order_id")
        .distinct()
        .count()
    )

    top_products = (
        order_items
        .values(
            "product_id",
            "product__name"
        )
        .annotate(
            sold=Sum("quantity"),
            revenue=Sum(
                F("price") * F("quantity"),
                output_field=DecimalField()
            )
        )
        .order_by("-sold")[:5]
    )

    return render(
        request,
        "store/partner/analytics.html",
        {
            "partner": profile,
            "total_products": total_products,
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "top_products": top_products,
        }
    )
    

@login_required
def partner_add_product(request):
    profile = getattr(request.user, "partner_profile", None)

    if not profile or not profile.is_active:
        raise PermissionDenied(
            "У вас нет доступа к добавлению товаров."
        )

    categories = Category.objects.all()
    tags = Tag.objects.all()

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        price_raw = request.POST.get("price", "").strip()
        stock_raw = request.POST.get("stock", "0").strip()
        category_id = request.POST.get("category")

        if not title or not price_raw or not category_id:
            return render(
                request,
                "store/partner/add_product.html",
                {
                    "partner": profile,
                    "categories": categories,
                    "tags": tags,
                    "error": "Название, цена и категория обязательны.",
                }
            )

        if len(title) > 40:
            return render(
                request,
                "store/partner/add_product.html",
                {
                    "partner": profile,
                    "categories": categories,
                    "tags": tags,
                    "error": "Название не может быть длиннее 40 символов.",
                }
            )

        try:
            price = Decimal(price_raw.replace(",", "."))
            stock = int(stock_raw)

            if price < 0 or stock < 0:
                raise ValueError

        except (InvalidOperation, ValueError, TypeError):
            return render(
                request,
                "store/partner/add_product.html",
                {
                    "partner": profile,
                    "categories": categories,
                    "tags": tags,
                    "error": "Проверьте цену и остаток.",
                }
            )

        category = get_object_or_404(
            Category,
            id=category_id
        )

        main_image = request.FILES.get("product_image")
        gallery_files = request.FILES.getlist("gallery_images")
        selected_tag_ids = request.POST.getlist("selected_tags")

        with transaction.atomic():
            product = Product.objects.create(
                name=title,
                category=category,
                image=main_image,
            )
            
            ProductListing.objects.create(
                product=product,
                owner=request.user,
                seller_type="partner",
                moderation_status="pending",
                is_active=True,
            )

            if selected_tag_ids:
                product.tags.set(selected_tag_ids)

            ProductDetails.objects.create(
                product=product,
                price=price,
                stock=stock,
            )

            for image in gallery_files[:10]:
                ProductImage.objects.create(
                    product=product,
                    image=image,
                )

        return redirect("partner_products")

    return render(
        request,
        "store/partner/add_product.html",
        {
            "partner": profile,
            "categories": categories,
            "tags": tags,
        }
    )
    
@login_required
def partner_edit_product(request, product_id):
    profile = getattr(request.user, "partner_profile", None)

    if not profile or not profile.is_active:
        raise PermissionDenied

    product = get_object_or_404(
        Product.objects.select_related(
            "listing",
            "details",
        ).prefetch_related(
            "images"
        ),
        id=product_id,
        listing__owner=request.user,
    )

    categories = Category.objects.all()
    tags = Tag.objects.all()

    if request.method == "POST":

        product.name = request.POST.get("title", "").strip()

        product.category = get_object_or_404(
            Category,
            id=request.POST.get("category")
        )

        if request.FILES.get("product_image"):
            product.image = request.FILES["product_image"]

        # снова отправляем на модерацию
        product.save()

        product.listing.status = "pending"
        product.listing.moderation_comment = ""
        product.listing.save()

        details = product.details
        details.price = Decimal(request.POST["price"].replace(",", "."))
        details.stock = int(request.POST["stock"])
        details.save()

        product.tags.set(request.POST.getlist("selected_tags"))

        # удалить выбранные фото
        delete_ids = request.POST.getlist("delete_gallery")

        if delete_ids:
            ProductImage.objects.filter(
                product=product,
                id__in=delete_ids
            ).delete()

        # добавить новые фото
        new_images = request.FILES.getlist("gallery_images")

        for image in new_images[:10]:
            ProductImage.objects.create(
                product=product,
                image=image,
            )

        return redirect("partner_products")

    return render(
        request,
        "store/partner/add_product.html",
        {
            "partner": profile,
            "product": product,
            "categories": categories,
            "tags": tags,
        },
    )


@login_required
def partner_register(request):

    if hasattr(request.user, "partner_profile"):
        return redirect("partner_dashboard")

    if request.method == "POST":

        PartnerProfile.objects.create(
            user=request.user,
            company_name=request.POST.get("company_name"),
            phone=request.POST.get("phone"),
            website=request.POST.get("website"),
            description=request.POST.get("description"),
            is_active=False,
            is_verified=False,
        )

        return redirect("partner_waiting")

    return render(
        request,
        "store/partner/register.html",
    )


@login_required
def partner_waiting(request):

    return render(
        request,
        "store/partner/waiting.html",
    )