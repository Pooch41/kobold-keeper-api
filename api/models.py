from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

import utils

class UserManager(BaseUserManager):
    def create_user(self, user_name: str, password=None, **extra_fields):
        if not user_name:
            raise ValueError("Users must have a unique, non-blank username!")

        user = self.model(user_name=user_name, **extra_fields)
        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_superuser(self, user_name: str, password=None, **extra_fields):
        superuser = self.create_user(user_name, password, **extra_fields)
        superuser.is_staff = True
        superuser.is_superuser = True

        superuser.save()
        return superuser


class User(AbstractBaseUser):
    user_name = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)

    #checks if the user is moderator
    is_staff = models.BooleanField(default=False)

    #checks if the user is administrator
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'user_name'
    REQUIRED_FIELDS = []


class RecoveryKey(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE, primary_key=True)
    # key to recover password, essentially second password TODO: hash this too
    recovery_key = models.CharField(max_length=10, unique=True, default=utils.generate_unique_key)

class Group(models.Model):
    group_name = models.CharField(max_length=100)
    # 1-1 group-owner, characters attached to group
    owner = models.ForeignKey('User', on_delete=models.CASCADE)


class Character(models.Model):
    character_name = models.CharField(max_length=100)
    character_note = models.CharField(max_length=256, blank=True)
    group = models.ForeignKey('Group', on_delete=models.CASCADE)

    #allows DM to mark NPCs
    is_npc = models.BooleanField(default=False)

class Roll(models.Model):
    character = models.ForeignKey('Character', on_delete=models.CASCADE)
    group = models.ForeignKey('Group', on_delete=models.CASCADE)

    #roll formula
    roll_input = models.CharField(max_length=512)

    #calculated roll total
    roll_value = models.IntegerField()

    #only dice rolls, separately ({"dice_type": [roll1, roll2...]})
    raw_dice_rolls = models.JSONField(default=dict)



