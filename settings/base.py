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

INSTALLED_APPS = (
    'django.contrib.humanize',
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
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'default',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'blingaleague': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
