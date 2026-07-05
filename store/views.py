import logging
from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product, ProductDetails

logger = logging.getLogger(__name__)

# Главная страница магазина — теперь рендерит шаблон store.html
def index(request):
    all_products=Product.objects.select_related('details').all()
    total = all_products.count()

    new_products = all_products.order_by('-created_at')[:4]     # последние 10 добавленные товары
    
    popular_product = all_products.order_by('-details__sales_count')[:4]

    context={
        'total': total,
        'new_products': new_products,
        'popular_products': popular_product
}
    return render(request, 'store/store.html', context=context)

# Страница "О нас" — тоже переводим на шаблон (создадим одельную страницу позже, если нужно)
def about(request):
    return render(request, 'store/about.html')


# Страница "Контакты" (если нужна как отдельная страница, помимо футера)
def contact(request):
    return render(request, 'contact.html')

# Вывод продуктов по GET-фильтрам
def product(request):
    name = request.GET.get('name', '')
    data = request.GET.get('data', '')
    response = f'Фильтр товаров: Название={name}, Доп.данные={data}'
    return HttpResponse(response)

# Добавление продукта (обработка POST) — переводим на шаблон add_product.html
@csrf_exempt
def add_product(request):
    if request.method == "POST":
        title = request.POST.get('title')
        price = request.POST.get('price')
        stock = request.POST.get('stock') or 0
        
        if not title or not price:
            logger.warning("Попытка создания товара без названия или цены")
            return HttpResponse('Поле названия и цены не может быть пустым!', status=400)
        
        try:
            with transaction.atomic():
                new_product = Product.objects.create(name=title)
                ProductDetails.objects.create(
                    product=new_product,
                    price=price,
                    stock=stock
                )
            logger.info(f'Создан новый продукт: {new_product.name} (ID: {new_product.id})')
            return HttpResponse(f'Товар "{title}" успешно добавлен с ID {new_product.id}!')
            
        except Exception as e:
            logger.error(f'Ошибка при добавлении товара в БД: {str(e)}', exc_info=True)
            return HttpResponse('Произошла внутренняя ошибка при сохранении товара.', status=500)

    # Вместо строки с HTML-формой просто вызываем шаблон страницы добавления
    return render(request, 'store/add_product.html')
    
# Детальная страница товара
def product_detail(request, product_id):
    product_item = get_object_or_404(Product.objects.select_related('details'), id=product_id)
    return render(request, 'product_detail.html', {'product': product_item})

# Кастомная страница 404
def page_not_found(request, exception):
    return render(request, '404.html', status=404)
