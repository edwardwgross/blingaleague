import ctypes

from django.db import models


class ShortUrl(models.Model):
    full_url = models.CharField(unique=True, max_length=255)
    short_url = models.CharField(unique=True, max_length=200)

    def _generate_short_url(self):
        return ctypes.c_uint64(hash(self.full_url)).value.to_bytes(8, 'big').hex()

    def save(self, *args, **kwargs):
        self.short_url = self._generate_short_url()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_url

    def __repr__(self):
        return str(self)
