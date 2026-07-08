from decimal import Decimal, InvalidOperation
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.http import  HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.dateparse import parse_date
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from .models import AdminProfile, Product, ProductDetails, ProductImage, RecentlyViewed, Cart, CartItem, Order, OrderItem, TagProposal,Tag, Category, WishList, WishlistItem
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



def is_any_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
def admin_dashboard(request):
    """Главный пульт управления для всех админов"""
    
    # Жесткая проверка: если пользователь не суперпользователь и не персонал — выдаем 403 ошибку
    if not (request.user.is_superuser or request.user.is_staff):
        raise PermissionDenied("Доступ запрещен. Страница только для администраторов.")
        
    AdminProfile.objects.get_or_create(user=request.user)
    
    is_main_admin = request.user.is_superuser
    
    # Автоматически создаем профиль прав для текущего админа, если его вдруг нет в БД
    AdminProfile.objects.get_or_create(user=request.user)
    
    is_main_admin = request.user.is_superuser
    profile = AdminProfile.objects.filter(user=request.user).first()
    
    # Проверяем, может ли этот админ редактировать ценники (Главный админ может всегда)
    can_edit_price = is_main_admin or (profile and profile.can_change_prices)

    # 📦 2. ПОИСК ЗАКАЗОВ (По товару и по точной дате)
    orders_queryset = Order.objects.prefetch_related('items').all()
    search_product = request.GET.get('search_product', '')
    search_date = request.GET.get('search_date', '')

    if search_product:
        orders_queryset = orders_queryset.filter(items__product_name__icontains=search_product)
        
    if search_date:
        parsed_date = parse_date(search_date)
        if parsed_date:
            orders_queryset = orders_queryset.filter(created_at__date=parsed_date)

    # 🏷️ 3. СБОРДАННЫХ КАТАЛОГА ДЛЯ ТАБЛИЦ ПАНЕЛИ
    products = Product.objects.select_related('details').all()
    categories = Category.objects.all()
    tags = Tag.objects.all()
    
    # Подтягиваем заявки на новые теги, которые ждут одобрения Главного Админа
    proposals = TagProposal.objects.select_related('product', 'proposed_by').all()
    
    # Список всех админов сайта для управления их галочками допусков
    all_admins = User.objects.filter(is_staff=True).select_related('admin_profile')

    # Передаем всё в HTML-шаблон админки
    context = {
        'is_main_admin': is_main_admin,
        'can_edit_price': can_edit_price,
        'orders': orders_queryset,
        'products': products,
        'categories': categories,
        'tags': tags,
        'proposals': proposals,
        'all_admins': all_admins,
        'search_product': search_product,
        'search_date': search_date,
    }
    return render(request, 'store/admin_dashboard.html', context)

# --- ДЕЙСТВИЯ С ЗАКАЗАМИ ---
@login_required
def admin_cancel_order(request, order_id):
    if not (request.user.is_superuser or request.user.is_staff):
        raise PermissionDenied()
    order = get_object_or_404(Order, id=order_id)
    order.is_paid = False
    order.save()
    return redirect('admin_dashboard')

@login_required
def admin_delete_order(request, order_id):
    """Удаление заказа (Только Главный админ)"""
    if not request.user.is_superuser:
        return HttpResponse("Доступ запрещен. Только для Главного Админа.", status=403)
    order = get_object_or_404(Order, id=order_id)
    order.delete()
    return redirect('admin_dashboard')


# 2. Изменение цены товара
@login_required
def admin_update_price(request, product_id):
    if not (request.user.is_superuser or request.user.is_staff):
        raise PermissionDenied()
        
    profile = AdminProfile.objects.filter(user=request.user).first()
    has_permission = request.user.is_superuser or (profile and profile.can_change_prices)
    
    if not has_permission:
        raise PermissionDenied("У вас нет разрешения на изменение цен.")
        
    if request.method == "POST":
        new_price = request.POST.get('price')
        details = get_object_or_404(ProductDetails, product_id=product_id)
        details.price = new_price
        details.save()
    return redirect('admin_dashboard')


@login_required
@csrf_exempt
def admin_propose_tag(request):
    if request.method == "POST":
        tag_name = request.POST.get('tag_name', '').strip()
        product_id = request.POST.get('product_id', '').strip()
        
        if not tag_name:
            return HttpResponse("Название тега не может быть пустым!", status=400)
            
        # ⚡ ПРОВЕРКА: Если product_id пустой — это принудительное создание тега админом напрямую в базу!
        if not product_id:
            # Создаем или находим тег сразу в глобальной базе данных
            tag, created = Tag.objects.get_or_create(name=tag_name)
            logger.info(f"Администратор напрямую создал глобальный тег: #{tag_name}")
            return redirect('admin_dashboard')
            
        # Старая логика: если товар существует (запрос пришел от обычного пользователя)
        try:
            product = get_object_or_404(Product, id=int(product_id))
            TagProposal.objects.create(name=tag_name, product=product)
            logger.info(f"Покупатель предложил тег #{tag_name} для товара ID {product_id}")
            return redirect('product_detail', product_id=product.id)
        except (ValueError, TypeError):
            return HttpResponse("Некорректный ID товара!", status=400)
            
    return redirect('admin_dashboard')


@login_required
def admin_approve_tag(request, proposal_id):
    """Главный админ утверждает тег и связывает его с товаром"""
    if not request.user.is_superuser:
        return HttpResponse("Доступ ограничен.", status=403)
        
    proposal = get_object_or_404(TagProposal, id=proposal_id)
    tag, created = Tag.objects.get_or_create(name=proposal.name)
    proposal.product.tags.add(tag)
    proposal.delete()
    return redirect('admin_dashboard')


# --- УПРАВЛЕНИЕ ДРУГИМИ АДМИНАМИ (Только Главный админ) ---
@login_required
def admin_toggle_permission(request, user_id):
    if not request.user.is_superuser:
        return HttpResponse("Доступ запрещен.", status=403)
    target_user = get_object_or_404(User, id=user_id)
    profile, created = AdminProfile.objects.get_or_create(user=target_user)
    profile.can_change_prices = not profile.can_change_prices
    profile.save()
    return redirect('admin_dashboard')



# Создание новой категории (Только для Главного Админа)
@login_required
def admin_create_category(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Доступ запрещен. Только для Главного Админа.")
        
    if request.method == "POST":
        category_name = request.POST.get('category_name', '').strip()
        if category_name:
            # get_or_create защитит от создания дубликатов с одинаковым именем
            Category.objects.get_or_create(name=category_name)
            logger.info(f"Главный админ {request.user.username} создал категорию: '{category_name}'")
            
    return redirect('admin_dashboard')




# --- ЗОНА ОГРАНИЧЕННОГО ДОСТУПА (ДЛЯ МЕНЕДЖЕРОВ И АДМИНОВ) ---
# Добавление продукта с гарантированной валидацией цены Decimal и мульти-галереей
@login_required
@permission_required('store.add_product', raise_exception=True)
@csrf_exempt
def add_product(request):
    if request.method == "POST":
        title = request.POST.get('title')
        price_raw = request.POST.get('price')
        stock = request.POST.get('stock') or 0
        category_id = request.POST.get('category')
        
        if not title or not price_raw or not category_id:
            logger.warning("Попытка создания товара без названия, цены или категории")
            return HttpResponse('Поля названия, цены и категории не могут быть пустыми!', status=400)
            
        if len(title) > 40:
            return HttpResponse('Название товара не может быть длиннее 40 символов!', status=400)
            
        # ⚡ ЗАЩИТА DECIMAL: Проверяем и жестко переводим цену в числовой формат
        try:
            price_clean = str(price_raw).replace(',', '.').strip()
            price_decimal = Decimal(price_clean)
        except (InvalidOperation, ValueError):
            return HttpResponse('Некорректный формат цены! Введите число, например: 499.99', status=400)
        
        try:
            category_obj = get_object_or_404(Category, id=category_id)
            
            # Читаем файлы картинок и массив выбранных тегов
            uploaded_main_image = request.FILES.get('product_image')
            gallery_files = request.FILES.getlist('gallery_images')
            selected_tag_ids = request.POST.getlist('selected_tags')
            
            # ⚡ ВСЕ ОПЕРАЦИИ ВНУТРИ ОДНОЙ АТОМАРНОЙ ТРАНЗАКЦИИ (Без дубликатов!)
            with transaction.atomic():
                # 1. Создаем основной товар
                new_product = Product.objects.create(
                    name=title, 
                    category=category_obj,
                    image=uploaded_main_image
                )
                
                # 2. Привязываем выбранные теги к созданному товару
                if selected_tag_ids:
                    new_product.tags.set(selected_tag_ids)
                
                # 3. Создаем базовые детали (цена, остаток)
                ProductDetails.objects.create(
                    product=new_product,
                    price=price_decimal,
                    stock=stock
                )
                
                # 4. Сохраняем дополнительные фотографии в галерею (лимит 10 штук)
                for f in gallery_files[:10]:
                    ProductImage.objects.create(
                        product=new_product,
                        image=f
                    )
                    
            logger.info(f'Создан товар {new_product.name} (ID: {new_product.id}). Тегов: {len(selected_tag_ids)}. Галерея: {len(gallery_files[:10])} шт.')
            return redirect('admin_dashboard')
            
        except Exception as e:
            logger.error(f'Ошибка добавления товара с галереей и тегами в БД: {str(e)}', exc_info=True)
            return HttpResponse('Произошла ошибка при сохранении товара в базу данных.', status=500)

    return render(request, 'store/add_product.html')


@login_required
@permission_required('store.delete_product', raise_exception=True)
def delete_product(request, product_id):
    product_item = get_object_or_404(Product, id=product_id)
    product_name = product_item.name
    
    try:
        product_item.delete()
        logger.info(f'Администратор удалил товар: {product_name} (ID: {product_id})')
        # ⚡ ИСПРАВЛЕНИЕ: Возвращаем админа обратно в пульт управления, а не на страницу гостя!
        return redirect('admin_dashboard')
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
            
            # Если товар уже лежал в корзине без галочки, при повторном добавлении активируем её
            cart_item.is_checked = True
            cart_item.save()
                
        logger.info(f"Гость {user_ip} добавил товар '{product_item.name}' в корзину.")
        return redirect('cart_detail') # Перенаправляем сразу в корзину для наглядности
        
    except Exception as e:
        logger.error(f"Ошибка добавления в корзину для IP {user_ip}: {str(e)}", exc_info=True)
        return HttpResponse("Ошибка при добавлении товара в корзину.", status=500)


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
                product_details = item.product.details
                
                if product_details.stock < item.quantity:
                    return HttpResponse(f"Недостаточно товара '{item.product.name}' на складе!", status=400)
                
                # Уменьшаем остаток и увеличиваем продажи
                product_details.stock -= item.quantity
                product_details.sales_count += item.quantity
                product_details.save()
                
                total_sum += product_details.price * item.quantity
                
                items_to_create.append(OrderItem(
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



# Переключатель галочки товара в корзине (Переключает состояние 🟩 и ⬜ для покупки)
def toggle_cart_item(request, item_id):
    user_ip = get_client_ip(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart__ip_address=user_ip)
    cart_item.is_checked = not cart_item.is_checked
    cart_item.save()
    return redirect('cart_detail')


# Добавление / Удаление товара из Отмеченного (Избранного на 24 часа)
def toggle_wishlist(request, product_id):
    user_ip = get_client_ip(request)
    product_item = get_object_or_404(Product, id=product_id)
    
    wishlist, created = WishList.objects.get_or_create(ip_address=user_ip)
    wishlist_item = WishlistItem.objects.filter(wishlist=wishlist, product=product_item).first()

    if wishlist_item:
        wishlist_item.delete()
    else:
        WishlistItem.objects.create(wishlist=wishlist, product=product_item)
        
    # Возвращает покупателя на ту страницу, на которой он стоял в этот момент
    return redirect(request.META.get('HTTP_REFERER', 'index'))


# Полное удаление товара из корзины гостя
def remove_from_cart(request, product_id):
    user_ip = get_client_ip(request)
    cart = get_object_or_404(Cart, ip_address=user_ip)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    
    cart_item.delete()
    logger.info(f"Гость {user_ip} полностью удалил товар ID {product_id} из корзины.")
    return redirect('cart_detail')






# store/views.py
import os
from django.conf import settings

# 1. ОБНОВЛЕНИЕ ИЛИ ДОБАВЛЕНИЕ ГЛАВНОГО ФОТО ТОВАРА ИЗ МЕДИАЦЕНТРА
@login_required
@permission_required('store.change_product', raise_exception=True)
def admin_update_product_photo(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        new_image = request.FILES.get('product_image')
        
        if new_image:
            # Если старое фото было, физически удаляем его с жесткого диска, чтобы не копить мусор
            if product.image:
                old_path = os.path.join(settings.MEDIA_ROOT, str(product.image))
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            product.image = new_image
            product.save()
            logger.info(f"Администратор обновил главное фото товара ID {product.id}")
            
    return redirect('admin_dashboard')

# 2. ПОЛНОЕ УДАЛЕНИЕ ФОТО ТОВАРА (ГЛАВНОГО ИЛИ ИЗ ГАЛЕРЕИ)
@login_required
@permission_required('store.change_product', raise_exception=True)
def admin_delete_product_photo(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    photo_type = request.GET.get('type', 'main') # Получаем параметр: main или gallery
    
    if photo_type == 'main' and product.image:
        # Физически стираем файл обложки с диска компьютера
        old_path = os.path.join(settings.MEDIA_ROOT, str(product.image))
        if os.path.exists(old_path):
            os.remove(old_path)
        # Очищаем поле в БД
        product.image = None
        product.save()
        logger.info(f"Администратор полностью стер главное фото товара ID {product.id}")
        
    elif photo_type == 'gallery':
        image_id = request.GET.get('image_id')
        if image_id:
            extra_img = get_object_or_404(ProductImage, id=image_id, product=product)
            # Удаляем файл ракурса с диска
            img_path = os.path.join(settings.MEDIA_ROOT, str(extra_img.image))
            if os.path.exists(img_path):
                os.remove(img_path)
            # Сносим запись из таблицы галереи
            extra_img.delete()
            logger.info(f"Администратор удалил доп. ракурс ID {image_id} у товара ID {product.id}")

    return redirect('admin_dashboard')
