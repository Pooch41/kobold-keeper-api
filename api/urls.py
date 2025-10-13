from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .viewsets import GroupViewSet, CharacterViewSet, RollViewSet, UserRegistrationViewSet
from .authentication import CustomTokenObtainPairView, PasswordResetWithKeyView

router = DefaultRouter()

router.register(r'groups', GroupViewSet, basename='group')
router.register(r'characters', CharacterViewSet, basename='character')
router.register(r'roll-history', RollViewSet, basename='roll-history')

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password-reset/', PasswordResetWithKeyView.as_view(), name='password_reset'),

    path('register/', UserRegistrationViewSet.as_view({'post': 'create'}), name='user_register'),

    path('roll/', RollViewSet.as_view({'post': 'create'}), name='create_roll'),

    path('', include(router.urls)),
]
