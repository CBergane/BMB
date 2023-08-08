from django.shortcuts import render
from cart.cart import Cart

def add_to_cart(request, produkt_id):
    cart = Cart(request)
    cart.add(produkt_id)

    return render(request, 'cart/menu_cart.html')