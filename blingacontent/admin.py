from django.contrib import admin
from django.db import models
from django.forms.widgets import Textarea

from .models import Meme, Gazette


class GazetteAdmin(admin.ModelAdmin):
    readony_fields = ('slug_url',)

    formfield_overrides = {
        models.TextField: {
            'widget': Textarea(attrs={'rows': 30, 'cols': 100}),
        }
    }


admin.site.register(Meme)
admin.site.register(Gazette, GazetteAdmin)
