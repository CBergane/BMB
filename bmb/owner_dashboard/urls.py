from django.urls import path

from .views import dashboard


app_name = 'owner_dashboard'

urlpatterns = [
    path('', dashboard, name='dashboard'),
]
