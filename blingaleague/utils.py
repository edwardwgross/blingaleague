import pygal

from django.contrib.humanize.templatetags.humanize import ordinal
from django.core.cache import caches


CACHE = caches['blingaleague']

MEMCACHE_KEY_LENGTH_LIMIT = 250

GRAPH_DEFAULT_OPTIONS = {
    'width': 600,
    'height': 400,
    'margin': 12,
    'max_scale': 6,
    'js': [],
}


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

        if len(cache_key) > MEMCACHE_KEY_LENGTH_LIMIT:
            return self.func(obj)

        if cache_key in obj.__dict__:
            return obj.__dict__[cache_key]

        if cache_key in CACHE:
            return CACHE.get(cache_key)

        value = self.func(obj)

        obj.__dict__[cache_key] = value
        CACHE.set(cache_key, value)

        return value


def clear_cached_properties():
    CACHE.clear()


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


def _graph_html(graph_class, x_data, y_series, **custom_options):
    graph_options = GRAPH_DEFAULT_OPTIONS.copy()
    graph_options.update(custom_options)

    graph = graph_class(**graph_options)

    graph.x_labels = x_data

    for (y_name, y_data) in y_series:
        graph.add(y_name, y_data)

    return graph.render()


def line_graph_html(x_data, y_series, **custom_options):
    return _graph_html(pygal.Line, x_data, y_series, **custom_options)


def bar_graph_html(x_data, y_series, **custom_options):
    return _graph_html(pygal.Bar, x_data, y_series, **custom_options)


def scatter_graph_html(x_data, y_series, **custom_options):
    graph_options = GRAPH_DEFAULT_OPTIONS.copy()
    graph_options.update(custom_options)

    graph = pygal.XY(**graph_options)

    for (y_name, y_data) in y_series:
        graph.add(y_name, list(zip(x_data, y_data)))

    return graph.render()


def rank_over_time_graph_html(
    time_data,
    raw_rank_series,
    total_teams,
    rank_cutoff,
    **custom_options
):
    graph_options = {
        'title': 'Rank over Time',
        'width': 800,
        'min_scale': total_teams - 1,
        'max_scale': total_teams - 1,
        'range': (0, total_teams - 1),
        'y_labels_major': [total_teams - rank_cutoff],
        'value_formatter': lambda x: ordinal(total_teams - x),
    }

    graph_options.update(custom_options)

    rank_series = {}
    for name, values in raw_rank_series.items():
        rank_series[name.title()] = [total_teams - value for value in values]

    return line_graph_html(
        time_data,  # x_data
        sorted(rank_series.items()),  # y_series
        **graph_options,
    )
