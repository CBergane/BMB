from django.urls import path
from .views import start_order, start_swish_order

urlpatterns = [
    path('start_order/', start_order, name='start_order'),
    path('start_swish_order/', start_swish_order, name='start_swish_order'),
]
