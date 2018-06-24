from django.contrib import admin

from .models import Member, Game, Season, FakeMember


admin.site.register(Member)
admin.site.register(Game)
admin.site.register(Season)
admin.site.register(FakeMember)
