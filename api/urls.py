"""
URL Configuration for the API application.

This module defines the main routes for the Kobold Keeper API, including:
1. RESTful routes for Group, Character, and Roll models via DefaultRouter.
2. Standard authentication routes (token, refresh, register).
3. Custom analytical endpoints for calculating luck statistics.
"""


from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .authentication import RegisterView, PasswordChangeView, PasswordResetWithKeyView
from .views import (GroupViewSet, CharacterViewSet, RollViewSet,
                    LuckAnalyticsView, LuckiestRollerView)

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'characters', CharacterViewSet, basename='character')
router.register(r'rolls', RollViewSet, basename='roll')

auth_urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('password/reset/', PasswordResetWithKeyView.as_view(), name='password_reset_with_key'),
]
urlpatterns = [
    *router.urls,
    path('auth/', include(auth_urlpatterns)),
    path('analytics/luck/', LuckAnalyticsView.as_view(), name='luck-analytics'),
    path('analytics/luckiest-roller/', LuckiestRollerView.as_view(), name='luckiest-roller'),

]
