from django.urls import path
from store import partner_views

from . import views
from . import cart_views
from . import admin_views
from . import seller_dashboard
from . import seller_views

urlpatterns = [
    # =========================================================
    # ГЛАВНЫЕ СТРАНИЦЫ МАГАЗИНА
    # =========================================================
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('product/', views.product, name='product'),
    path(
        'product/<int:product_id>/',
        views.product_detail,
        name='product_detail'
    ),
    #========================================================
    # КОРЗИНА, ИЗБРАННОЕ И ИСТОРИЯ
    # cart_views.py
    #========================================================
    path(
        'cart/',
        cart_views.cart_detail,
        name='cart_detail'
    ),

    path(
        'cart/add/<int:product_id>/',
        cart_views.add_to_cart,
        name='add_to_cart'
    ),

    path(
        'cart/checkout/',
        cart_views.checkout,
        name='checkout'
    ),

    path(
        'cart/toggle/<int:item_id>/',
        cart_views.toggle_cart_item,
        name='toggle_cart_item'
    ),

    path(
        'cart/remove/<int:product_id>/',
        cart_views.remove_from_cart,
        name='remove_from_cart'
    ),

    path(
        'wishlist/toggle/<int:product_id>/',
        cart_views.toggle_wishlist,
        name='toggle_wishlist'
    ),

    path(
        'wishlist/',
        cart_views.wishlist_detail,
        name='wishlist_detail'
    ),

    path(
        'history/',
        cart_views.history_detail,
        name='history_detail'
    ),


    # =========================================================
    # DASHBOARD — ВХОД / ВЫХОД
    # admin_views.py
    # =========================================================

    path(
        'secret-backend-zone-2026/login/',
        admin_views.dashboard_login,
        name='dashboard_login'
    ),

    path(
        'secret-backend-zone-2026/logout/',
        admin_views.dashboard_logout,
        name='dashboard_logout'
    ),

    path(
        'secret-backend-zone-2026/dashboard/',
        admin_views.admin_dashboard,
        name='admin_dashboard'
    ),


    # =========================================================
    # УПРАВЛЕНИЕ ТОВАРАМИ
    # admin_views.py
    # =========================================================

    path(
        'add_product/',
        admin_views.add_product,
        name='add_product'
    ),

    path(
        'product/<int:product_id>/delete/',
        admin_views.delete_product,
        name='delete_product'
    ),

    path(
        'secret-backend-zone-2026/product/<int:product_id>/update-photo/',
        admin_views.admin_update_product_photo,
        name='admin_update_product_photo'
    ),

    path(
        'secret-backend-zone-2026/product/<int:product_id>/delete-photo/',
        admin_views.admin_delete_product_photo,
        name='admin_delete_product_photo'
    ),

    path(
        'secret-backend-zone-2026/product/price/<int:product_id>/',
        admin_views.admin_update_price,
        name='admin_update_price'
    ),

    path(
        "secret-backend-zone-2026/product/<int:product_id>/toggle-active/",
        admin_views.toggle_product_active,
        name="toggle_product_active",
    ),
    path(
        'secret-backend-zone-2026/product/stock/<int:product_id>/',
        admin_views.admin_update_stock,
        name='admin_update_stock'
    ),

    # =========================================================
    # УПРАВЛЕНИЕ ЗАКАЗАМИ
    # admin_views.py
    # =========================================================

    path(
        'secret-backend-zone-2026/order/cancel/<int:order_id>/',
        admin_views.admin_cancel_order,
        name='admin_cancel_order'
    ),

    path(
        'secret-backend-zone-2026/order/delete/<int:order_id>/',
        admin_views.admin_delete_order,
        name='admin_delete_order'
    ),


    # =========================================================
    # ТЕГИ И КАТЕГОРИИ
    # admin_views.py
    # =========================================================

    path(
        'secret-backend-zone-2026/tag/propose/',
        admin_views.admin_propose_tag,
        name='admin_propose_tag'
    ),

    path(
        'secret-backend-zone-2026/tag/approve/<int:proposal_id>/',
        admin_views.admin_approve_tag,
        name='admin_approve_tag'
    ),

    path(
        'secret-backend-zone-2026/category/create/',
        admin_views.admin_create_category,
        name='admin_create_category'
    ),

    # маршруты для партнеров 
    path(
        "partner/dashboard/",
        partner_views.partner_dashboard,
        name="partner_dashboard"
    ),

    path(
        "partner/products/",
        partner_views.partner_products,
        name="partner_products"
    ),

    path(
        "partner/orders/",
        partner_views.partner_orders,
        name="partner_orders"
    ),

    path(
        "partner/analytics/",
        partner_views.partner_analytics,
        name="partner_analytics"
    ),
    
    path(
        "partner/products/add/",
        partner_views.partner_add_product,
        name="partner_add_product",
    ),

    # =========================================================
    # УПРАВЛЕНИЕ ПРАВАМИ РЕДАКТОРОВ
    # admin_views.py
    # =========================================================

    path(
        'secret-backend-zone-2026/admin-rules/toggle/<int:user_id>/',
        admin_views.admin_toggle_permission,
        name='admin_toggle_permission'
    ),
    
    path(
        "product/<int:product_id>/approve/",
        admin_views.approve_product,
        name="approve_product",
    ),

    path(
        "product/<int:product_id>/reject/",
        admin_views.reject_product,
        name="reject_product",
    ),
    
    # повторная отправка на одобрения 
    path(
        "partner/product/<int:product_id>/edit/",
        partner_views.partner_edit_product,
        name="partner_edit_product",
    ),
    
    
    
    path(
        "seller/register/",
        views.become_seller,
        name="become_seller",
    ),

    path(
        "seller/dashboard/",
        seller_dashboard.seller_dashboard,
        name="seller_dashboard",
    ),
    
    # urls.py

    path(
        "seller/product/add/",
        seller_views.seller_add_product,
        name="seller_add_product"
    ),
    path(
        "seller/products/",
        seller_views.seller_products,
        name="seller_products",
        ),
    
    path(
        "seller/product/<int:product_id>/edit/",
        seller_views.seller_edit_product,
        name="seller_edit_product",
    ),
    
    path(
        "partner/register/",
        partner_views.partner_register,
        name="partner_register",
    ),

    path(
        "partner/waiting/",
        partner_views.partner_waiting,
        name="partner_waiting",
    ),
    
]


# Кастомная страница 404 остаётся в обычном views.py
handler404 = 'store.views.page_not_found'

