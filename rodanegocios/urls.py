
from django.contrib import admin
from django.urls import path, include
from core import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    #path('', views.HomeView.as_view(), name='home'),
    #path("empresas/", include("empresas.urls")),
]
