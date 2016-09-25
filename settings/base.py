import os

SECRET_KEY = 's4nders0n'

DEBUG = True
TEMPLATE_DEBUG = DEBUG

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

