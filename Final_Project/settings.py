import os

from django.conf.global_settings import ALLOWED_HOSTS, SECRET_KEY

SECRET_KEY='django-insecure-6ja+)_xtz)f%fn!&wq!c1h_g-xfaxs!#48h%rz2l4pd7)-@eyo'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEBUG=True

ALLOWED_HOSTS=[]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

AUTH_USER_MODEL = 'Payroll_app.CustomUser'
AUTHENTICATION_BACKENDS = (
    'Payroll_app.backends.EmailAuthBackend',
    'django.contrib.auth.backends.ModelBackend', )

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # 会话数据存储在数据库中
SESSION_COOKIE_NAME = 'sessionid'  # 默认 cookie 名称
SESSION_COOKIE_AGE = 1800  # Expiration in 30 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',  # 开发环境
        # Redis is recommended for production environments:
        # 'BACKEND': 'django_redis.cache.RedisCache',
        # 'LOCATION': 'redis://127.0.0.1:6379/1'
        'TIMEOUT': 300,  # Default cache time (seconds)
    }
}

INSTALLED_APPS=[
    'django.contrib.admin',
    'Payroll_app.apps.PayrollAppConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
   # 'sslserver',
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

INSTALLED_APPS += ['crispy_bootstrap5']
CRISPY_ALLOWED_TEMPLATE_PACKS = ['bootstrap5']
CRISPY_TEMPLATE_PACK = 'bootstrap5'

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_ratelimit.middleware.RatelimitMiddleware',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'payroll_system_db',
        'USER': 'postgres',
        'PASSWORD': 'yyxdmima',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

ROOT_URLCONF = 'Final_Project.urls'

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR,'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Final_Project.wsgi.application'

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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # 示例：Gmail SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'yuy759250@gmail.com'  # 你的邮箱地址
EMAIL_HOST_PASSWORD = 'olsv ivtf goin wcea'  # 生成的应用专用密码
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER