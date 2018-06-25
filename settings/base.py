import os

SECRET_KEY = 's4nders0n'

INFO = False
TEMPLATE_INFO = INFO

ALLOWED_HOSTS = (
    'www.blingaleague.com',
    'blingaleague.com',
    '34.221.179.171',
)

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
    'markdown_filter',
    'blingacontent',
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

TEMPLATE_CONTEXT_PROCESSORS = (
    'blingacontent.context_processors.memes',
    'django.contrib.auth.context_processors.auth',
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
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': None,
    }
}

PAGE_CACHE_DEFAULT_TIMEOUT = 365 * 24 * 60 * 60

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

MARKDOWN_FILTER_WHITELIST_TAGS = [
    'a',
    'p',
    'code',
    'h1',
    'h2',
    'h3',
    'ol',
    'ul',
    'li',
    'em',
    'strong',
]
