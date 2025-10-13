from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password, **extra_fields):
        """Creates and saves a Superuser with the given username and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username


class RecoveryKey(models.Model):
    """
    Stores a unique, system-generated recovery key hash for secure account recovery.
    The raw key is generated in the serializer and immediately hashed before saving here.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    recovery_key_hash = models.CharField(max_length=128, unique=True)

    def set_key(self, raw_key):
        self.recovery_key_hash = make_password(raw_key)

    def check_key(self, raw_key):
        return check_password(raw_key, self.recovery_key_hash)

    def __str__(self):
        return f"Recovery Key for {self.user.username}"

    class Meta:
        db_table = 'recovery_keys'
        verbose_name = 'Recovery Key'

class Group(models.Model):
    group_name = models.CharField(max_length=100)
    # 1-1 group-owner, characters attached to group
    owner = models.ForeignKey('User', on_delete=models.CASCADE)


class Character(models.Model):
    character_name = models.CharField(max_length=100)
    character_note = models.CharField(max_length=256, blank=True)
    group = models.ForeignKey('Group', on_delete=models.CASCADE)

    # allows DM to mark NPCs
    is_npc = models.BooleanField(default=False)


class Roll(models.Model):
    character = models.ForeignKey('Character', on_delete=models.CASCADE)
    group = models.ForeignKey('Group', on_delete=models.CASCADE)

    # roll formula
    roll_input = models.CharField(max_length=512)

    # calculated roll total
    roll_value = models.IntegerField()

    # only dice rolls, separately ({"dice_type": [roll1, roll2...]})
    raw_dice_rolls = models.JSONField(default=dict)
