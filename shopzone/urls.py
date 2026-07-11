# shopzone/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.db import connection

urlpatterns = [
    # 1. Системная сине-белая админка Django для создания юзеров и раздачи прав
    path('secret-backend-zone-2026-system/', admin.site.urls), 
    
    # 2. Подключаем маршруты вашего приложения store
    path('', include('store.urls')), 
]

# ⚡ УСКОРИТЕЛЬ БАЗЫ ДАННЫХ: Включаем WAL-режим автоматически при старте
try:
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
except Exception:
    # Игнорируем ошибку, если миграции еще не запускались
    pass

# ⚡ ДОБАВЛЯЕМ ЭТО УСЛОВИЕ: Разрешаем Django показывать картинки из папки media во время разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
