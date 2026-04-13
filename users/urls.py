from django.urls import path
from . import views

urlpatterns = [
    path('request-api/', views.RequestCodeAPIView.as_view(), name='api-request'),
    path('verify-api/', views.VerifyCodeAPIView.as_view(), name='api-verify'),
    path('profile-api/', views.ProfileAPIView.as_view(), name='api-profile'),
    path('logout-api/', views.LogoutAPIView.as_view(), name='api-logout'),

    path('login/', views.LoginTemplateView.as_view(), name='login'),
    path('verify/', views.VerifyTemplateView.as_view(), name='verify'),
    path('profile/', views.ProfileTemplateView.as_view(), name='profile'),
    path('logout/', views.LogoutTemplateView.as_view(), name='logout'),
]