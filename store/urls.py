from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('product/', views.product, name='product'),
    path('add_product/', views.add_product, name='add_product'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    
    # МАРШРУТЫ ДЛЯ КОРЗИНЫ И ОПЛАТЫ
    path('cart/', views.cart_detail, name='cart_detail'), 
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'), 
    path('cart/checkout/', views.checkout, name='checkout'), # <-- ДОБАВИЛИ ЭТУ СТРОКУ
]

handler404 = 'store.views.page_not_found'
