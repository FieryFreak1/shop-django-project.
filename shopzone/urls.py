from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Исправили admin.site.register на admin.site.urls
    path('secret-backend-zone-2026/', admin.site.urls), 
    
    # Подключаем маршруты нашего магазина
    path('', include('store.urls')), 
]
