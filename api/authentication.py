from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    UserPasswordChangeSerializer,
    PasswordResetWithKeySerializer
)

User = get_user_model()


class RegisterView(CreateAPIView):
    """
    Allows new users to create an account.

    - Inherits from CreateAPIView for simple POST-based model creation.
    - Uses the UserSerializer to handle data validation and user creation.
    - Permission is set to AllowAny, meaning any unauthenticated user can access this endpoint.
    """
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = [AllowAny]


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Extends the default JWT TokenObtainPairView to customize the token generation process.

    This view is hit when a user logs in (typically via POST of username/password).
    The CustomTokenObtainPairSerializer is used to inject custom user data (like
    permissions or profile details) into the JWT payload.
    """
    serializer_class = CustomTokenObtainPairSerializer


class PasswordChangeView(APIView):
    """
    Allows a logged-in user to change their own password.

    This endpoint requires the user to be authenticated and submit their old password
    along with the new one for validation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = UserPasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password successfully updated."},
            status=status.HTTP_200_OK
        )


class PasswordResetWithKeyView(APIView):
    """
    Handles the final step of a password reset flow.

    The user provides a temporary key (usually sent via email) and a new password.
    This endpoint is public (AllowAny) because the user is not yet logged in.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetWithKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password successfully reset. You can now log in."},
            status=status.HTTP_200_OK
        )
