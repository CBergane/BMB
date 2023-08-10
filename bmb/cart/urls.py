from django.urls import path

from cart.views import add_to_cart, cart, checkout

urlpatterns = [
    path('add_to_cart/<int:produkt_id>/', add_to_cart, name='add_to_cart'),
    path('', cart, name='cart'),
    path('checkout/', checkout, name='checkout'),
]