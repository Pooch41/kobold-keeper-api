from django.contrib import admin

from .models import Group, Character, Roll


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Registers the Group model. Groups are the primary container for collaborative
    roll history and character management."""
    list_display = ('id', 'group_name', 'owner')
    search_fields = ('group_name',)


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    """Registers the Character model, which serves as a simple tag to segment
    rolls for different entities within a group (e.g., Player 1, Player 2, NPC)."""
    list_display = ('id', 'character_name', 'user', 'group', 'is_npc')
    list_filter = ('group', 'user', 'is_npc')
    search_fields = ('character_name',)


@admin.register(Roll)
class RollAdmin(admin.ModelAdmin):
    """Registers the core Roll model. This is where all the raw and processed
    dice data is stored. Most fields are read-only as the data is generated
    during the API call and should not be manually altered post-save."""
    list_display = ('id', 'character', 'roll_value', 'rolled_at')
    list_filter = ('character__user', 'group')
    readonly_fields = ('roll_input', 'roll_value', 'raw_dice_rolls',
                       'character', 'group', 'rolled_at')
