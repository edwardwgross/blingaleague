from django.contrib import admin
from django.db import models
from django.forms.widgets import NumberInput

from .models import Member, Game, Season, FakeMember


class GameAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.IntegerField: {
            'widget': NumberInput(attrs={'type': 'number'}),
        }
    }


admin.site.register(Member)
admin.site.register(Game, GameAdmin)
admin.site.register(Season)
admin.site.register(FakeMember)
