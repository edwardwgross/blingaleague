from pathlib import Path

#DEBUG = TEMPLATE_DEBUG = True

#DJANGO_CPROFILE_MIDDLEWARE_REQUIRE_STAFF = False

SECRET_KEY = 's4nders0n'

INFO = False
TEMPLATE_INFO = INFO

ALLOWED_HOSTS = (
    'www.blingaleague.com',
    'blingaleague.com',
    #'54.202.50.88',
    '35.92.50.225',
)

ROOT_URLCONF = 'blingaleague.urls'
FORCE_SCRIPT_NAME = ''

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_ROOT = BASE_DIR / 'static'
STATIC_URL = '/static/'

DATA_DIR = BASE_DIR / 'data'

LOGIN_URL = 'login'
LOGOUT_URL = 'logout'
LOGIN_REDIRECT_URL = 'blingaleague.home'

FULL_SITE_URL = 'https://blingaleague.com'

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = '8735061745-nbbkebaqtd706bd6pkfo7opvsu3u61fd.apps.googleusercontent.com'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = 'ceIa4DpTNtL8cdcX_k68c9wP'

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'request',
    'social_django',
    'markdown_filter',
    'tagging',
    'blingacontent',
    'blingaleague',
    'blingalytics',
)

TEMPLATE_DIRS = (
    BASE_DIR / 'blingaleague' / 'templates' / 'blingaleague',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Django 1.7: 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    #'request.middleware.RequestMiddleware',  # 2019-10-02 request/models.py having issues with user model
    'django.contrib.messages.middleware.MessageMiddleware',
    #'django_cprofile_middleware.middleware.ProfilerMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    #'blingacontent.context_processors.memes',
    'blingaleague.context_processors.auth_member',
    'django.contrib.auth.context_processors.auth',
    'django.template.context_processors.request',
    'social_django.context_processors.backends',
    'social_django.context_processors.login_redirect',
)

AUTHENTICATION_BACKENDS = (
    'social_core.backends.open_id.OpenIdAuth',
    'social_core.backends.google.GoogleOpenId',
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'blingaleague',
        'USER': 'livecommish',
        'PASSWORD': open(
            BASE_DIR / 'settings' / 'mysql_password.txt',
            'r',
        ).read().strip(),
        'HOST': 'localhost',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': None,
        'KEY_PREFIX': 'default-',
        'OPTIONS': {
            'MAX_ENTRIES': 3000,
        },
    },
    'blingaleague': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': None,
        'KEY_PREFIX': 'blingaleague-',
        'OPTIONS': {
            'MAX_ENTRIES': 3000,
        },
    },
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
            'filename': BASE_DIR / 'logs' / 'django.log',
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

FORCE_LOWERCASE_TAGS = True
