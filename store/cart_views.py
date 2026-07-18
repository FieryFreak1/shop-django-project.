import logging

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect

from store.models import Cart, CartItem, Order, OrderItem, Product, RecentlyViewed, WishList, WishlistItem
from store.utils import get_client_ip

logger = logging.getLogger(__name__)



# Добавление товара в гостевую корзину
def add_to_cart(request, product_id):
    user_ip = get_client_ip(request)
    product_item = get_object_or_404(Product, id=product_id)

    listing = product_item.listing

    if (
        not listing.is_active
        or listing.moderation_status != "approved"
    ):
        return HttpResponse(
            "Этот товар ещё не прошёл модерацию.",
            status=400
        )

    # Проверяем наличие деталей
    if not hasattr(product_item, "details"):
        return HttpResponse(
            "Для товара не указаны данные о наличии.",
            status=400
        )

    if product_item.details.stock <= 0:
        return HttpResponse(
            "Товара нет в наличии.",
            status=400
        )

# дальше идет обычное добавление в корзину    
    try:
        with transaction.atomic():
            cart, created = Cart.objects.get_or_create(ip_address=user_ip)
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                product=product_item
            )
            if not item_created:
                cart_item.quantity += 1
            
            # Если товар уже лежал в корзине без галочки, при повторном добавлении активируем её
            cart_item.is_checked = True
            cart_item.save()
                
        logger.info(f"Гость {user_ip} добавил товар '{product_item.name}' в корзину.")
        return redirect('cart_detail') # Перенаправляем сразу в корзину для наглядности
        
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
        return HttpResponse("Ваша корзина пуста.", status=400)
    
    # Фильтруем только те элементы корзины, где стоит галочка (is_checked=True)
    checked_items = cart.items.filter(is_checked=True)
    
    if not checked_items.exists():
        return HttpResponse("Вы не выбрали ни одного товара для покупки! Отметьте галочками нужные товары.", status=400)
    
    try:
        with transaction.atomic():
            total_sum = 0
            items_to_create = []
            
            for item in checked_items:
                '''проверка наличия товара '''
                if (
                    not item.product.listing.is_active
                    or item.product.listing.moderation_status != "approved"
                ):
                    return HttpResponse(
                        f"Товар '{item.product.name}' ещё не прошёл модерацию.",
                        status=400
                    )
                product_details = item.product.details
                
                if product_details.stock < item.quantity:
                    return HttpResponse(f"Недостаточно товара '{item.product.name}' на складе!", status=400)
                
                # Уменьшаем остаток и увеличиваем продажи
                product_details.stock -= item.quantity
                product_details.sales_count += item.quantity
                product_details.save()
                
                total_sum += product_details.price * item.quantity
                
                items_to_create.append(OrderItem(
                    product=item.product,
                    product_name=item.product.name,
                    price=product_details.price,
                    quantity=item.quantity
                ))
            
            # Создаем оформленный заказ
            order = Order.objects.create(
                ip_address=user_ip,
                total_price=total_sum,
                is_paid=True
            )
            
            # Привязываем элементы к заказу
            for order_item in items_to_create:
                order_item.order = order
            OrderItem.objects.bulk_create(items_to_create)
            
            # ВАЖНО: Удаляем только КУПЛЕННЫЕ товары. 
            # Товары без галочек остаются в корзине ждать своего часа!
            checked_items.delete()
            
            # Если в корзине вообще ничего не осталось, удаляем саму корзину
            if not cart.items.exists():
                cart.delete()
            
        logger.info(f"Гость {user_ip} успешно оплатил отмеченные товары. Код: {order.unique_code}")
        return render(request, 'store/order_success.html', {'order': order})
        
    except Exception as e:
        logger.error(f"Ошибка при оформлении заказа для IP {user_ip}: {str(e)}", exc_info=True)
        return HttpResponse("Произошла ошибка при обработке платежа.", status=500)
    
    
    

# Переключатель галочки товара в корзине (Переключает состояние 🟩 и ⬜ для покупки)
def toggle_cart_item(request, item_id):
    user_ip = get_client_ip(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart__ip_address=user_ip)
    cart_item.is_checked = not cart_item.is_checked
    cart_item.save()
    return redirect('cart_detail')




# Полное удаление товара из корзины гостя
def remove_from_cart(request, product_id):
    user_ip = get_client_ip(request)
    cart = get_object_or_404(Cart, ip_address=user_ip)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    
    cart_item.delete()
    logger.info(f"Гость {user_ip} полностью удалил товар ID {product_id} из корзины.")
    return redirect('cart_detail')




# Добавление / Удаление товара из Отмеченного (Избранного на 24 часа)
def toggle_wishlist(request, product_id):
    user_ip = get_client_ip(request)
    product_item = get_object_or_404(
        Product.objects.select_related("listing"),
        id=product_id,
        listing__is_active=True,
        listing__moderation_status="approved",
    )
    
    wishlist, created = WishList.objects.get_or_create(ip_address=user_ip)
    wishlist_item = WishlistItem.objects.filter(wishlist=wishlist, product=product_item).first()

    if wishlist_item:
        wishlist_item.delete()
    else:
        WishlistItem.objects.create(wishlist=wishlist, product=product_item)
        
    # Возвращает покупателя на ту страницу, на которой он стоял в этот момент
    return redirect(request.META.get('HTTP_REFERER', 'index'))



# Страница просмотра Отмеченных товаров (Избранного)
def wishlist_detail(request):
    user_ip = get_client_ip(request)
    wishlist = WishList.objects.filter(ip_address=user_ip).prefetch_related('items__product__details').first()
    return render(request, 'store/wishlist_detail.html', {'wishlist': wishlist})



# Страница просмотра Истории просмотров (Лимит 100)
def history_detail(request):
    user_ip = get_client_ip(request)
    # Вытаскиваем все просмотры гостя (до 100 штук)
    history = RecentlyViewed.objects.filter(ip_address=user_ip).select_related('product__details').order_by('-viewed_at')[:100]
    return render(request, 'store/history_detail.html', {'history': history})
