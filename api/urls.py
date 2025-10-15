from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import GroupViewSet, CharacterViewSet,RollViewSet
from .authentication import RegisterView, PasswordChangeView, PasswordResetWithKeyView

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
]
