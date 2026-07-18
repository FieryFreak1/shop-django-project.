import logging
import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required ,permission_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt

from .permissions import dashboard_permission, partner_update_stock

from .forms import StoreContactForm
from .models import (
    AdminProfile,
    Category,
    CustomUser,
    Order,
    Product,
    ProductDetails,
    ProductImage,
    StoreContact,
    Tag,
    TagProposal,
    ProductListing,
)

from .permissions import partner_update_stock

logger = logging.getLogger(__name__)


@login_required
def admin_dashboard(request):
    """Главный пульт управления для администраторов"""

    # ===================================================
    # Если это партнёр — отправляем в кабинет партнёра
    # ===================================================
    partner = getattr(request.user, "partner_profile", None)

    pending_products = (
        Product.objects.filter(
            listing__moderation_status="pending"
        )
        .select_related(
            "listing",
            "category",
            "details",
        )
    )
    if partner and partner.is_active:
        return redirect("partner_dashboard")

    # ===================================================
    # Ниже обычная админка
    # ===================================================

    is_main_admin = request.user.is_superuser

    profile = AdminProfile.objects.filter(
        user=request.user
    ).first()

    can_edit_price = (
        is_main_admin or
        (profile and profile.can_change_prices)
    )

    contact_instance = StoreContact.objects.last()

    # ============================================
    # Создание редактора
    # ============================================
    if request.method == "POST" and "create_editor" in request.POST:

        username = request.POST.get("username")
        password = request.POST.get("password")

        if not CustomUser.objects.filter(username=username).exists():

            user = CustomUser.objects.create_user(
                username=username,
                password=password,
            )

            user.is_staff = False
            user.is_superuser = False
            user.save()

            AdminProfile.objects.create(
                user=user,
                can_access_dashboard="can_access_dashboard" in request.POST,
                can_change_prices="can_change_prices" in request.POST,
                can_delete_products="can_delete_products" in request.POST,
                can_manage_orders="can_manage_orders" in request.POST,
            )

        return redirect("admin_dashboard")

    # ============================================
    # Сохранение контактов
    # ============================================
    if request.method == "POST" and is_main_admin:

        contacts_form = StoreContactForm(
            request.POST,
            instance=contact_instance
        )

        if contacts_form.is_valid():
            contacts_form.save()
            return redirect("admin_dashboard")

    else:
        contacts_form = StoreContactForm(
            instance=contact_instance
        )

    # ============================================
    # Поиск заказов
    # ============================================
    orders_queryset = Order.objects.prefetch_related(
        "items"
    ).all()

    search_product = request.GET.get(
        "search_product",
        ""
    )

    search_date = request.GET.get(
        "search_date",
        ""
    )

    if search_product:
        orders_queryset = orders_queryset.filter(
            items__product_name__icontains=search_product
        )

    if search_date:
        parsed_date = parse_date(search_date)

        if parsed_date:
            orders_queryset = orders_queryset.filter(
                created_at__date=parsed_date
            )

    # ============================================
    # Каталог
    # ============================================
    products = Product.objects.select_related(
        "details",
        "listing",
        "category",
    ).all()

    categories = Category.objects.all()

    tags = Tag.objects.all()

    proposals = TagProposal.objects.select_related(
        "product",
        "proposed_by"
    ).all()

    all_admins = (
        CustomUser.objects
        .filter(
            admin_profile__can_access_dashboard=True
        )
        .select_related("admin_profile")
    )

    context = {
        "is_main_admin": is_main_admin,
        "can_edit_price": can_edit_price,
        "orders": orders_queryset,
        "products": products,
        "categories": categories,
        "tags": tags,
        "proposals": proposals,
        "all_admins": all_admins,
        "search_product": search_product,
        "search_date": search_date,
        "is_admin_view": True,
        "contacts_form": contacts_form,
        "pending_products": pending_products,
    }

    return render(
        request,
        "store/admin_dashboard.html",
        context,
    )

def dashboard_login(request):

    if request.user.is_authenticated:
        partner_profile = getattr(request.user, "partner_profile", None)

        if partner_profile and partner_profile.is_active:
            return redirect("partner_dashboard")

        return redirect("admin_dashboard")

    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:
            error = "Неверный логин или пароль."

        else:
            # 1. Партнёр
            partner_profile = getattr(
                user,
                "partner_profile",
                None
            )

            if partner_profile and partner_profile.is_active:
                login(request, user)
                return redirect("partner_dashboard")

            # 2. Superuser или администратор
            admin_profile = getattr(
                user,
                "admin_profile",
                None
            )

            if user.is_superuser or (
                admin_profile
                and admin_profile.is_active
                and admin_profile.can_access_dashboard
            ):
                login(request, user)
                return redirect("admin_dashboard")

            error = "У вас нет доступа к панели управления."

    return render(
        request,
        "store/dashboard_login.html",
        {
            "error": error
        }
    )
    
    
def dashboard_logout(request):
    logout(request)
    return redirect("dashboard_login")



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
                    image=uploaded_main_image,
                    owner=request.user
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
    product_item = partner_update_stock(request, product_id)
    product_name = product_item.name
    
    try:
        product_item.delete()
        logger.info(f'Администратор удалил товар: {product_name} (ID: {product_id})')
        # ⚡ ИСПРАВЛЕНИЕ: Возвращаем админа обратно в пульт управления, а не на страницу гостя!
        return redirect('admin_dashboard')
    except Exception as e:
        logger.error(f'Ошибка при удалении товара ID {product_id}: {str(e)}', exc_info=True)
        return HttpResponse('Ошибка при удалении товара.', status=500)



# 1. ОБНОВЛЕНИЕ ИЛИ ДОБАВЛЕНИЕ ГЛАВНОГО ФОТО ТОВАРА ИЗ МЕДИАЦЕНТРА
@login_required
@permission_required("store.change_product", raise_exception=True)
def admin_update_product_photo(request, product_id):
    product = partner_update_stock(request, product_id)

    if request.method == "POST":
        new_image = request.FILES.get("product_image")

        if new_image:
            if product.image:
                product.image.delete(save=False)

            product.image = new_image
            product.save(update_fields=["image"])

            logger.info(
                f"Пользователь {request.user.username} обновил "
                f"главное фото товара ID {product.id}"
            )

    return redirect("admin_dashboard")



# 2. ПОЛНОЕ УДАЛЕНИЕ ФОТО ТОВАРА (ГЛАВНОГО ИЛИ ИЗ ГАЛЕРЕИ)
@login_required
@permission_required('store.change_product', raise_exception=True)
def admin_delete_product_photo(request, product_id):
    product = partner_update_stock(request, product_id)
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

@login_required
def admin_update_stock(request, product_id):
    product = partner_update_stock(request, product_id)

    if request.method == "POST":
        try:
            new_stock = int(request.POST.get("stock", 0))

            if new_stock < 0:
                return HttpResponse(
                    "Остаток не может быть отрицательным.",
                    status=400
                )

            details = get_object_or_404(
                ProductDetails,
                product=product
            )

            details.stock = new_stock
            details.save(update_fields=["stock"])

            logger.info(
                f"Пользователь {request.user} изменил остаток "
                f"товара '{product.name}' (ID: {product.id}) "
                f"на {new_stock}"
            )

            return redirect("admin_dashboard")

        except (ValueError, TypeError):
            return HttpResponse(
                "Некорректное количество товара.",
                status=400
            )

    return HttpResponse("Метод не разрешён.", status=405)

# 2. Изменение цены товара
@login_required
@dashboard_permission("can_change_prices")
def admin_update_price(request, product_id):
    product = partner_update_stock(request, product_id)
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




# Создание новой категории (Только для Главного Админа)
@login_required
@dashboard_permission("can_manage_categories")
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


def is_any_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)
from django.shortcuts import render, redirect  # Убедитесь, что redirect импортирован
from .forms import StoreContactForm           # <-- ДОБАВЬТЕ ИМПОРТ ФОРМЫ


# ДЛЯ БЛОКИРОВКИ ТОВАРА 
@login_required
def toggle_product_active(request, product_id):
    product = partner_update_stock(request, product_id)

    if request.method == "POST":
        product.is_active = not product.is_active
        product.save(update_fields=["is_active"])

    return redirect("admin_dashboard")

@login_required
def approve_product(request, product_id):

    if not request.user.is_superuser:
        raise PermissionDenied

    product = get_object_or_404(
        Product,
        id=product_id
    )

    listing = getattr(
        product,
        "listing",
        None
    )

    if not listing:
        return HttpResponse(
            "У товара нет объявления для модерации",
            status=400
        )


    listing.moderation_status = "approved"
    listing.is_active = True
    listing.moderation_comment = ""
    listing.save()


    return redirect(
        "admin_dashboard"
    )

@login_required
def reject_product(request, product_id):

    if not request.user.is_superuser:
        raise PermissionDenied


    product = get_object_or_404(
        Product,
        id=product_id
    )


    listing = product.listing


    if request.method == "POST":

        listing.moderation_status = "rejected"

        listing.is_active = False

        listing.moderation_comment = request.POST.get(
            "comment",
            ""
        )

        listing.save()


        return redirect(
            "admin_dashboard"
        )


    return render(
        request,
        "store/reject_product.html",
        {
            "product": product,
        },
    )
    
    