SECRET_KEY = 's4nders0n'

DEBUG = True
TEMPLATE_DEBUG = DEBUG

INSTALLED_APPS = (
    'blingaleague',
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

