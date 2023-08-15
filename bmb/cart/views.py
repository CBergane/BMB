from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .cart import Cart
from products.models import Produkt

def add_to_cart(request, produkt_id):
    cart = Cart(request)
    cart.add(produkt_id)

    return render(request, 'cart/partials/menu_cart.html')

def cart(request):
    return render(request, 'cart/cart.html')

def success(request):
    return render(request, 'cart/success.html')

def update_cart(request, produkt_id, action):
    cart = Cart(request)

    if action == 'increment':
        cart.add(produkt_id, 1, True)
    else:
        cart.add(produkt_id, -1, True)
    
    produkt = Produkt.objects.get(pk=produkt_id)
    quantity = cart.get_item(produkt_id)

    if quantity:
        quantity = quantity['quantity']

        item = {
            'produkt': {
                'id': produkt.id,
                'namn': produkt.namn,
                'image': produkt.image,
                'get_thumbnail': produkt.get_thumbnail(),
                'pris': produkt.pris,
                'slug': produkt.slug,
            },
            'total_price': (quantity * produkt.pris),
            'quantity': quantity,
        }
    else:
        item = None

    response = render(request, 'cart/partials/cart_item.html', {'item': item})
    response['HX-Trigger'] = 'update-menu-cart'

    return response

@login_required
def checkout(request):
    pub_key = settings.STRIPE_API_KEY_PUBLISHABLE
    return render(request, 'cart/checkout.html', {'pub_key': pub_key})

def hx_menu_cart(request):
    return render(request, 'cart/partials/menu_cart.html')

def hx_cart_total(request):
    return render(request, 'cart/partials/cart_total.html')