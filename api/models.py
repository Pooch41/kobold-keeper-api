from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

from .utils import generate_key


class CustomUserManager(BaseUserManager):
    """
    Custom manager for the User model, required when using a custom user model.
    It defines how to create regular users and superusers.
    """

    def create_user(self, username, password=None, **extra_fields):
        """Creates and saves a regular User with the given username and password."""
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
    """
    Custom user model that uses username as the unique identifier instead of email.
    It extends AbstractBaseUser for authentication and PermissionsMixin for Django's
    permission framework.
    """
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
    Stores a hashed, temporary recovery key for a user. This is a one-time
    use key for password reset, hashed to ensure the plain key is never stored.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    recovery_key_hash = models.CharField(max_length=128, unique=True)

    def set_key(self, raw_key):
        """Hashes the raw key using Django's standard password hashing."""
        self.recovery_key_hash = make_password(raw_key)

    def check_key(self, raw_key):
        """Checks a raw key string against the stored hash."""
        return check_password(raw_key, self.recovery_key_hash)

    def __str__(self):
        return f"Recovery Key for {self.user.username}"

    class Meta:
        db_table = 'recovery_keys'
        verbose_name = 'Recovery Key'

    @classmethod
    def create_and_hash_key(cls, user_instance):
        """
        Class method to generate a new raw key, hash it, save the instance,
        and return the raw key for the user to use.
        """
        raw_key = generate_key()
        recovery_key_instance = cls(user=user_instance)
        recovery_key_instance.set_key(raw_key)
        recovery_key_instance.save()

        return raw_key


class Group(models.Model):
    """
    Represents a group or campaign context that multiple users or characters
    might roll in. This allows for filtering rolls for a shared campaign environment.
    """
    group_name = models.CharField(max_length=100)
    # 1-1 group-owner, characters attached to group
    owner = models.ForeignKey('User', on_delete=models.CASCADE)

    def __str__(self):
        return self.group_name


class Character(models.Model):
    """
    Represents a simple character profile, acting as a tag for rolls.
    This allows a user (e.g., a GM) to track rolls for different entities
    without requiring a full character sheet system.
    """
    character_name = models.CharField(max_length=100)
    character_note = models.CharField(max_length=256, blank=True)
    group = models.ForeignKey('Group', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='characters')
    is_npc = models.BooleanField(default=False)

    def __str__(self):
        return self.character_name


class Roll(models.Model):
    """
    The core model for the application, storing the history of every dice roll
    executed by a user. This data powers the Luck Analytics Service.
    """
    character = models.ForeignKey('Character', on_delete=models.CASCADE)
    group = models.ForeignKey('Group', on_delete=models.CASCADE)
    roll_input = models.CharField(max_length=512)
    roll_value = models.IntegerField()
    raw_dice_rolls = models.JSONField(default=dict)
    rolled_at = models.DateTimeField(default=timezone.now)
    luck_index = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Roll {self.roll_value} for {self.character.character_name}"

class DailyLuckRecord(models.Model):
    """
    Stores the daily record of the 'luckiest' character based on the
    average roll vs. theoretical average (Luck Index).
    """
    date = models.DateField(unique = True,)
    character = models.ForeignKey('Character', on_delete=models.PROTECT)
    character_name_snapshot = models.CharField(max_length=255)
    group_name_snapshot = models.CharField(max_length=255)
    luck_index = models.FloatField()
    total_rolls_parsed = models.IntegerField(validators=[MinValueValidator(1)])
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date} - {self.character.character_name} (Index: {self.luck_index:.4f})"

class GroupPerformanceRecord(models.Model):
    """
    Stores the pre-calculated, long-term performance statistics for a Group.
    This record is updated daily by a scheduled Celery task.
    """
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='performance_record')

    average_luck_index = models.FloatField(default=0.0)
    total_rolls = models.IntegerField(default=0)

    lowest_roll = models.IntegerField(null=True, blank=True)
    highest_roll = models.IntegerField(null=True, blank=True)


    luckiest_player_name = models.CharField(max_length=255, default="N/A")
    luckiest_player_score = models.FloatField(default=0.0)

    least_lucky_player_name = models.CharField(max_length=255, default="N/A")
    least_lucky_player_score = models.FloatField(default=0.0)


    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Performance for {self.group.name} (Luck: {self.average_luck_index:.4f})"
