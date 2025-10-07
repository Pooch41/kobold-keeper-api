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
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'user_name'
    REQUIRED_FIELDS = []


class RecoveryKey(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE, primary_key=True)
    recovery_key = models.CharField(max_length=10, unique=True, default=utils.generate_unique_key)

class Group(models.Model):
    group_name = models.CharField(max_length=100)
    owner_id = models.ForeignKey('User', on_delete=models.CASCADE)
    group_raw_avg = models.FloatField(null=True, default=None)
    group_raw_min = models.IntegerField(null=True, default=None)
    group_raw_max = models.IntegerField(null=True, default=None)
    group_mod_avg = models.FloatField(null=True, default=None)
    group_mod_min = models.IntegerField(null=True, default=None)
    group_mod_max = models.IntegerField(null=True, default=None)


class Character(models.Model):
    pass
