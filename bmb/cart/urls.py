from django.urls import path
from cart.views import (
    add_to_cart,
    cart,
    checkout,
    hx_menu_cart,
    update_cart,
    hx_cart_total,
    success,
    clear_cart,
    update_cart_quantity,
)

urlpatterns = [
    path('', cart, name='cart'),
    path('success/', success, name='success'),
    path('checkout/', checkout, name='checkout'),
    path('cart/clear/', clear_cart, name='clear_cart'),
    path('add_to_cart/<int:produkt_id>/', add_to_cart, name='add_to_cart'),
    path('update_cart/<str:cart_key>/<str:action>/', update_cart, name='update_cart'),
    path('update_cart_quantity/<str:cart_key>/<str:action>/', update_cart_quantity, name='update_cart_quantity'),
    path('hx_menu_cart/', hx_menu_cart, name='hx_menu_cart'),
    path('hx_cart_total/', hx_cart_total, name='hx_cart_total'),
]