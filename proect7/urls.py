"""
URL configuration for proect7 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from app import views as app_views  

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', app_views.home, name='home'),  # Используем app_views
    path('auth/', app_views.auth_view, name='auth_view'),
    path('register/', app_views.register, name='register'),
    path('login/', app_views.login_view, name='login'),
    path('logout/', app_views.logout_view, name='logout'),
    path('services/', app_views.services_view, name='services'),
    path('services/<str:category>/', app_views.services_category_view, name='services_category'),
    path('appointment/', app_views.make_appointment, name='make_appointment'),
    path('appointment/success/', app_views.appointment_success, name='appointment_success'),
    path('appointments/', app_views.appointment_list, name='appointment_list'),
    path('get-available-times/', app_views.get_available_times, name='get_available_times'),
    
    # Профиль пользователя
    path('profile/', app_views.profile_view, name='profile'),
    path('profile/edit/', app_views.edit_profile, name='edit_profile'),
    path('review/<int:appointment_id>/', app_views.create_review, name='create_review'),
    
    # История обслуживания
    path('service-history/', app_views.service_history, name='service_history'),
    
    # Чат
    path('chat/', include('chat.urls')), 
    
    # Новости и спец. предл
    path('news/manage/', app_views.manage_news, name='manage_news'),
    path('offers/manage/', app_views.manage_special_offers, name='manage_special_offers'),
    path('news-and-offers/', app_views.news_and_offers, name='news_and_offers'),
    path('news/edit/<int:news_id>/', app_views.edit_news, name='edit_news'),
    path('news/delete/<int:news_id>/', app_views.delete_news, name='delete_news'),
    path('offers/edit/<int:offer_id>/', app_views.edit_special_offer, name='edit_special_offer'),
    path('offers/delete/<int:offer_id>/', app_views.delete_special_offer, name='delete_special_offer'),
    # API endpoints
    path('api/available-times/', app_views.get_available_times, name='get_available_times'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

