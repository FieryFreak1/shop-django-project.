import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Product, RecentlyViewed, WishList
from .utils import get_client_ip


logger = logging.getLogger(__name__)



# Главная страница магазина
def index(request):
    user_ip = get_client_ip(request)
    logger.info(f"На главную страницу зашел гость с IP: {user_ip}")

    all_products = Product.objects.select_related('details').all()
    total = all_products.count()
    new_products = all_products.order_by('-created_at')[:4]
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
    product_item = get_object_or_404(Product.objects.select_related('details'), id=product_id)
    user_ip = get_client_ip(request)

    # Записываем товар в просмотренное для этого IP (или обновляем время просмотра)
    RecentlyViewed.objects.update_or_create(
        ip_address=user_ip,
        product=product_item
    )

    return render(request, 'store/product_detail.html', {'product': product_item})


# Кастомная страница 404
def page_not_found(request, exception):
    return render(request, '404.html', status=404)










