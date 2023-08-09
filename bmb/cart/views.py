from django.shortcuts import render
from cart.cart import Cart

def add_to_cart(request, produkt_id):
    cart = Cart(request)
    cart.add(produkt_id)

    return render(request, 'cart/menu_cart.html')

def cart(request):
    return render(request, 'cart/cart.html')

def checkout(request):
    return render(request, 'cart/checkout.html')