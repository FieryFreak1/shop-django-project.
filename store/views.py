import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, permission_required

# ИМПОРТИРУЕМ ВСЕ НАШИ МОДЕЛИ
from .models import Product, ProductDetails, StoreContact, Cart, CartItem, Order, OrderItem

# ИМПОРТИРУЕМ УТИЛИТУ ДЛЯ ОПРЕДЕЛЕНИЯ IP
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

    context = {
        'total': total,
        'new_products': new_products,
        'popular_products': popular_product,
        'user_ip': user_ip
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


# --- ЗОНА ОГРАНИЧЕННОГО ДОСТУПА (ДЛЯ МЕНЕДЖЕРОВ И АДМИНОВ) ---

# Добавление продукта
@login_required
@permission_required('store.add_product', raise_exception=True)
@csrf_exempt
def add_product(request):
    if request.method == "POST":
        title = request.POST.get('title')
        price = request.POST.get('price')
        stock = request.POST.get('stock') or 0
        
        if not title or not price:
            logger.warning("Попытка создания товара без названия или цены")
            return HttpResponse('Поле названия и цены не может быть пустым!', status=400)
        
        if len(title) > 40:
            return HttpResponse('Название товара не может быть длиннее 40 символов!', status=400)
        
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

    return render(request, 'store/add_product.html')


# Удаление продукта (Только для Главного Админа)
@login_required
@permission_required('store.delete_product', raise_exception=True)
def delete_product(request, product_id):
    product_item = get_object_or_404(Product, id=product_id)
    product_name = product_item.name
    
    try:
        product_item.delete()
        logger.info(f'Администратор удалил товар: {product_name} (ID: {product_id})')
        return redirect('index')
    except Exception as e:
        logger.error(f'Ошибка при удалении товара ID {product_id}: {str(e)}', exc_info=True)
        return HttpResponse('Ошибка при удалении товара.', status=500)


# --- ЗОНА ГОСТЕВОЙ КОРЗИНЫ И ОПЛАТЫ ПО IP ---

# Добавление товара в гостевую корзину
def add_to_cart(request, product_id):
    user_ip = get_client_ip(request)
    product_item = get_object_or_404(Product, id=product_id)
    
    try:
        with transaction.atomic():
            cart, created = Cart.objects.get_or_create(ip_address=user_ip)
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                product=product_item
            )
            if not item_created:
                cart_item.quantity += 1
                cart_item.save()
                
        logger.info(f"Гость {user_ip} добавил товар '{product_item.name}' в корзину. Количество: {cart_item.quantity}")
        return HttpResponse(f"Товар '{product_item.name}' успешно добавлен в корзину!")
        
    except Exception as e:
        logger.error(f"Ошибка добавления в корзину для IP {user_ip}: {str(e)}", exc_info=True)
        return HttpResponse("Ошибка при добавлении товара в корзину.", status=500)


# Просмотр содержимого корзины
def cart_detail(request):
    user_ip = get_client_ip(request)
    cart = Cart.objects.prefetch_related('items__product__details').filter(ip_address=user_ip).first()
    
    context = {
        'cart': cart,
    }
    return render(request, 'store/cart.html', context=context)


# Имитация оплаты и генерация уникального кода заказа
def checkout(request):
    user_ip = get_client_ip(request)
    cart = Cart.objects.prefetch_related('items__product__details').filter(ip_address=user_ip).first()
    
    if not cart or not cart.items.exists():
        return HttpResponse("Ваша корзина пуста. Нечего оплачивать.", status=400)
    
    try:
        with transaction.atomic():
            total_sum = 0
            items_to_create = []
            
            for item in cart.items.all():
                product_details = item.product.details
                
                if product_details.stock < item.quantity:
                    return HttpResponse(f"Недостаточно товара '{item.product.name}' на складе!", status=400)
                
                product_details.stock -= item.quantity
                product_details.sales_count += item.quantity
                product_details.save()
                
                total_sum += product_details.price * item.quantity
                
                items_to_create.append(OrderItem(
                    product_name=item.product.name,
                    price=product_details.price,
                    quantity=item.quantity
                ))
            
            order = Order.objects.create(
                ip_address=user_ip,
                total_price=total_sum,
                is_paid=True
            )
            
            for order_item in items_to_create:
                order_item.order = order
            OrderItem.objects.bulk_create(items_to_create)
            
            cart.delete()
            
        logger.info(f"Гость {user_ip} успешно оплатил заказ! Сгенерирован код: {order.unique_code}")
        return render(request, 'store/order_success.html', {'order': order})
        
    except Exception as e:
        logger.error(f"Ошибка при оформлении заказа для IP {user_ip}: {str(e)}", exc_info=True)
        return HttpResponse("Произошла ошибка при обработке платежа.", status=500)


# Детальная страница товара
def product_detail(request, product_id):
    product_item = get_object_or_404(Product.objects.select_related('details'), id=product_id)
    return render(request, 'product_detail.html', {'product': product_item})

# Кастомная страница 404
def page_not_found(request, exception):
    return render(request, '404.html', status=404)
