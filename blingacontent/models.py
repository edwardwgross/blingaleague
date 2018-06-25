from django.core.cache import caches
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string

from slugify import slugify

from blingaleague.models import Member, FakeMember
from blingaleague.utils import fully_cached_property


CACHE = caches['default']


class Meme(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()

    def save(self, *args, **kwargs):
        super(Meme, self).save(*args, **kwargs)
        CACHE.clear()

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)


class Gazette(models.Model):
    headline = models.CharField(max_length=500)
    published_date = models.DateField(default=None, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    slug = models.CharField(blank=True, null=True, max_length=200)
    use_markdown = models.BooleanField(default=True)

    @fully_cached_property
    def published_date_str(self):
        if self.published_date is None:
            return 'not published'

        return self.published_date.strftime('%-m/%-d/%Y')

    def save(self, *args, **kwargs):
        if self.published_date:
            self.slug = "{}-{}".format(
                self.published_date.strftime('%Y-%m-%d'),
                slugify(self.headline),
            )
        else:
            self.slug = None

        super(Gazette, self).save(*args, **kwargs)
        CACHE.clear()

    def __str__(self):
        return "{} - {}".format(
            self.published_date_str,
            self.headline,
        )
