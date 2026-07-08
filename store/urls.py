# store/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ГЛАВНЫЕ СТРАНИЦЫ МАГАЗИНА ДЛЯ ГОСТЕЙ
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('product/', views.product, name='product'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('add_product/', views.add_product, name='add_product'),
    
    # МАРШРУТЫ ДЛЯ КОРЗИНЫ И ОПЛАТЫ ГОСТЯ
    path('cart/', views.cart_detail, name='cart_detail'), 
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'), 
    path('cart/checkout/', views.checkout, name='checkout'),
    
        # Маршруты фоторедактора в медиацентре админки
    path('secret-backend-zone-2026/product/<int:product_id>/update-photo/', views.admin_update_product_photo, name='admin_update_product_photo'),
    path('secret-backend-zone-2026/product/<int:product_id>/delete-photo/', views.admin_delete_product_photo, name='admin_delete_product_photo'),

    
    # ⚡ ВОТ ЭТИ ТРИ СТРОЧКИ ОБЕСПЕЧИВАЮТ ПОЛНУЮ ЛОГИКУ КОРЗИНЫ И ЗВЕЗДОЧЕК:
    path('cart/toggle/<int:item_id>/', views.toggle_cart_item, name='toggle_cart_item'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'), # <-- ДОБАВИЛИ СЮДА

    # ====== ЗАКРЫТЫЙ ПУЛЬТ УПРАВЛЕНИЯ АДМИНИСТРАТОРА (6 БЛОКОВ) ======
    path('secret-backend-zone-2026/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('secret-backend-zone-2026/order/cancel/<int:order_id>/', views.admin_cancel_order, name='admin_cancel_order'),
    path('secret-backend-zone-2026/order/delete/<int:order_id>/', views.admin_delete_order, name='admin_delete_order'),
    path('secret-backend-zone-2026/product/price/<int:product_id>/', views.admin_update_price, name='admin_update_price'),
    path('secret-backend-zone-2026/tag/propose/', views.admin_propose_tag, name='admin_propose_tag'),
    path('secret-backend-zone-2026/tag/approve/<int:proposal_id>/', views.admin_approve_tag, name='admin_approve_tag'),
    path('secret-backend-zone-2026/admin-rules/toggle/<int:user_id>/', views.admin_toggle_permission, name='admin_toggle_permission'),
    path('secret-backend-zone-2026/category/create/', views.admin_create_category, name='admin_create_category'),
    
    # ОТДЕЛЬНЫЕ СТРАНИЦЫ ИЗБРАННОГО И ПРОСМОТРЕННОГО ПОЛЬЗОВАТЕЛЯ
    path('wishlist/', views.wishlist_detail, name='wishlist_detail'),
    path('history/', views.history_detail, name='history_detail'),
]

handler404 = 'store.views.page_not_found'
