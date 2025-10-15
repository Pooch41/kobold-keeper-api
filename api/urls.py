from rest_framework.routers import DefaultRouter
from .views import GroupViewSet, CharacterViewSet, RollViewSet

router = DefaultRouter()


router.register(r'groups', GroupViewSet, basename='group')

router.register(r'characters', CharacterViewSet, basename='character')

router.register(r'rolls', RollViewSet, basename='roll')

urlpatterns = router.urls
