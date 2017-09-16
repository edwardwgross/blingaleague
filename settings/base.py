import datetime
import os

SECRET_KEY = 's4nders0n'

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ('blingaleague.com',)

ROOT_URLCONF = 'blingaleague.urls'
FORCE_SCRIPT_NAME = ''

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

LOGIN_URL = '/login'
LOGOUT_URL = '/logout'
LOGIN_REDIRECT_URL = '/'

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'blingaleague',
    'blingalytics',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Django 1.7: 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'blingaleague',
        'USER': 'livecommish',
        'PASSWORD': 'Sanderson2008',
        'HOST': 'localhost',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1;11211',
        'TIMEOUT': 7 * 24 * 60 * 60,
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_logger': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'default',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'blingaleague': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
