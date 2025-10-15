from django.contrib import admin
from .models import Group, Character, Roll

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'group_name', 'owner')
    search_fields = ('group_name',)

@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ('id', 'character_name', 'user', 'group', 'is_npc')
    list_filter = ('group', 'user', 'is_npc')
    search_fields = ('character_name',)

@admin.register(Roll)
class RollAdmin(admin.ModelAdmin):
    list_display = ('id', 'character', 'roll_value', 'rolled_at')
    list_filter = ('character__user', 'group')
    readonly_fields = ('roll_input', 'roll_value', 'raw_dice_rolls', 'character', 'group', 'rolled_at')
