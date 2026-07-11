# shopzone/settings.py

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

AUTH_USER_MODEL = 'store.CustomUser'


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'dsnvfjsdnacoksanoidcnas'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Указываем Django, куда отправлять пользователей для входа в систему
LOGIN_URL = 'dashboard_login'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'store',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'shopzone.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], 
        'APP_DIRS': True,                 
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                'store.context_processors.global_store_data',
            ],
        },
    },
]


WSGI_APPLICATION = 'shopzone.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

# Базовый URL для открытия картинок в браузере
MEDIA_URL = '/media/'

# Физический путь к папке media на вашем компьютере
MEDIA_ROOT = BASE_DIR / 'media'





# Создаем папку для логов в корне проекта, если её нет
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        # Настройка внешнего вида строки лога
        'standard': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        # 1. Вывод логов в консоль терминала
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        # 2. Запись логов в файл (автоматически создает файл store.log)
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'store.log'),
            'formatter': 'standard',
            'encoding': 'utf-8', # Обязательно для поддержки русского языка
        },
    },
    'loggers': {
        # Настройки для приложений нашего проекта
        '': {  # Пустая строка означает корневой логгер (ловит всё)
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}


SESSION_EXPIRE_AT_BROWSER_CLOSE = True 
SESSION_SAVE_EVERY_REQUEST = True 
SESSION_COOKIE_AGE = 7200 
