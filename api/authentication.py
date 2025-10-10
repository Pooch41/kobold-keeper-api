from django.contrib.auth import authenticate, get_user_model
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.hashers import check_password

from .models import RecoveryKey

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username = attrs.get(User.USERNAME_FIELD)
        password = attrs.get('password')
        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )

        if user is None or not user.is_active:
            raise AuthenticationFailed(
                self.error_messages['no_active_account'],
                'no_active_account',
            )

        self.user = user
        return super().validate(attrs)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class PasswordResetWithKeySerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    recovery_key = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate(self, data):
        username = data.get('username')
        recovery_key = data.get('recovery_key')
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username})
        except User.DoesNotExist:
            raise ValidationError("Authentication failed. Invalid username or recovery key.")
        try:
            recovery_instance = RecoveryKey.objects.get(user=user)
        except RecoveryKey.DoesNotExist:
            raise ValidationError("Authentication failed. Invalid username or recovery key.")

        if not check_password(recovery_key, recovery_instance.recovery_key_hash):
            raise ValidationError("Authentication failed. Invalid username or recovery key.")

        self.user = user
        return data

    def save(self):

        new_password = self.validated_data.get('new_password')
        self.user.set_password(new_password)
        self.user.save()

        return self.user


class PasswordResetWithKeyView(TokenObtainPairView):
    serializer_class = PasswordResetWithKeySerializer

