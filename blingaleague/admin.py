from django.contrib import admin
from django.db import models
from django.forms.widgets import NumberInput

from .models import Member, Game, Postseason, FakeMember, \
                    Trade, TradedAsset, Keeper, DraftPick, \
                    PlayerNotes


class GameAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.IntegerField: {
            'widget': NumberInput(attrs={'type': 'number'}),
        }
    }


admin.site.register(Member)
admin.site.register(Game, GameAdmin)
admin.site.register(Postseason)
admin.site.register(FakeMember)
admin.site.register(Trade)
admin.site.register(TradedAsset)
admin.site.register(Keeper)
admin.site.register(DraftPick)
admin.site.register(PlayerNotes)
