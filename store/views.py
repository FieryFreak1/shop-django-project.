import logging
from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import PartnerProfile, Product, RecentlyViewed, WishList
from .utils import get_client_ip
from .models import SellerProfile

logger = logging.getLogger(__name__)



# Главная страница магазина
def index(request):
    user_ip = get_client_ip(request)
    logger.info(f"На главную страницу зашел гость с IP: {user_ip}")

    all_products = Product.objects.filter(
        listing__is_active=True,
        listing__moderation_status="approved",
    ).select_related(
        "details",
        "listing",
    )
    total = all_products.count()
    new_products = all_products.order_by("-listing__created_at")[:4]
    popular_product = all_products.order_by('-details__sales_count')[:4]

    # Ищем список желаний текущего гостя в базе данных по его IP
    wishlist = WishList.objects.filter(ip_address=user_ip).first()
    global_wishlist_ids = [item.product.id for item in wishlist.items.all()] if wishlist else []

    context = {
        'total': total,
        'new_products': new_products,
        'popular_products': popular_product,
        'user_ip': user_ip,
        'global_wishlist_ids': global_wishlist_ids,  # Теперь переменная существует и передается!
    }
    return render(request, 'store/store.html', context=context)


# Страница "О нас"
def about(request):
    return render(request, 'store/about.html')

# Страница "Контакты"
def contact(request):
    return render(request, 'contact.html')

# Вывод продуктов по GET-фильтрам
def product(request):
    name = request.GET.get('name', '')
    data = request.GET.get('data', '')
    response = f'Фильтр товаров: Название={name}, Доп.данные={data}'
    return HttpResponse(response)




# Детальная страница товара
def product_detail(request, product_id):

    product_item = get_object_or_404(
        Product.objects.select_related(
            "details",
            "listing"
        ),
        id=product_id,
        listing__is_active=True,
        listing__moderation_status="approved",
    )

    user_ip = get_client_ip(request)

    RecentlyViewed.objects.update_or_create(
        ip_address=user_ip,
        product=product_item
    )

    return render(
        request,
        'store/product_detail.html',
        {
            'product': product_item,
        }
    )


# Кастомная страница 404
def page_not_found(request, exception):
    return render(request, '404.html', status=404)




@login_required
def become_seller(request):
    if hasattr(request.user, "seller_profile"):
        return redirect("seller_dashboard")

    if request.method == "POST":

        phone = request.POST.get("phone")
        city = request.POST.get("city")

        SellerProfile.objects.create(
            user=request.user,
            phone=phone,
            city=city,
        )

        return redirect("seller_dashboard")

    return render(
        request,
        "store/seller/become_seller.html"
    )


@login_required
def seller_dashboard(request):

    seller = get_object_or_404(
        SellerProfile,
        user=request.user
    )

    return render(
        request,
        "store/seller/dashboard.html",
        {
            "seller": seller
        }
    )




@login_required
def partner_register(request):

    if hasattr(request.user, "partner_profile"):
        return redirect("partner_dashboard")

    if request.method == "POST":

        PartnerProfile.objects.create(
            user=request.user,
            company_name=request.POST["company_name"],
            phone=request.POST["phone"],
            website=request.POST["website"],
            description=request.POST["description"],
            is_active=False,
        )

        return render(
            request,
            "store/partner/waiting.html"
        )

    return render(
        request,
        "store/partner/register.html"
    )