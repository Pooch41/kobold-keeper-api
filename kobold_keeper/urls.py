from django.contrib import admin
from django.urls import path, include


from rest_framework_simplejwt.views import TokenRefreshView
from api import views as web_views
from api.authentication import CustomTokenObtainPairView, PasswordResetWithKeyView

urlpatterns = [
    path('admin/', admin.site.urls),


    path('', web_views.home, name='home'),
    path('about/', web_views.about, name='about'),
    path('docs/', web_views.docs, name='docs'),
    path('login/', web_views.login, name='login'),


    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/reset/', PasswordResetWithKeyView.as_view(), name='password_reset_with_key'),

    path('api/', include('api.urls')),
]
