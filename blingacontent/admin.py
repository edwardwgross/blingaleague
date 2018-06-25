from django.contrib import admin

from .models import Meme, Gazette


class GazetteAdmin(admin.ModelAdmin):
    readony_fields = ('slug_url',)


admin.site.register(Meme)
admin.site.register(Gazette, GazetteAdmin)
