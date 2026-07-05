from django.urls import path
from . import views

from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('product/', views.product, name='product'),
    path('add_product/', views.add_product, name='add_product'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    # Строки 'price' и 'product_description' мы удалили, так как этих функций больше нет во views.py
]

handler404 = 'store.views.page_not_found'
