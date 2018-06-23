from django.core.cache import caches


CACHE = caches['default']


class fully_cached_property(object):

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self

        if not hasattr(obj, 'cache_key'):
            return self.func(obj)

        cache_key = "{}|{}:{}".format(cls.__name__, obj.cache_key, self.func.__name__)

        if cache_key in obj.__dict__:
            return obj.__dict__[cache_key]

        if cache_key in CACHE:
            return CACHE.get(cache_key)

        value = self.func(obj)

        obj.__dict__[cache_key] = value
        CACHE.set(cache_key, value)

        return value


def int_to_roman(integer):
    if integer <= 0:
        return '?'

    num_map = (
        (1000, 'M'),
        (900, 'CM'),
        (500, 'D'),
        (400, 'CD'),
        (100, 'C'),
        (90, 'XC'),
        (50, 'L'),
        (40, 'XL'),
        (10, 'X'),
        (9, 'IX'),
        (5, 'V'),
        (4, 'IV'),
        (1, 'I'),
    )

    roman = ''

    while integer > 0:
        for i, r in num_map:
            if integer >= i:
                roman += r
                integer -= i
                break

    return roman
