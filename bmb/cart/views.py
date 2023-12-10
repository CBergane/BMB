from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

from .cart import Cart
from django.shortcuts import get_object_or_404, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from products.models import Produkt

def add_to_cart(request, produkt_id):
    produkt = get_object_or_404(Produkt, pk=produkt_id)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))  # Default to 1 if no quantity was specified
        
        # Check if the desired quantity is available
        if quantity > produkt.inventory:
            quantity = produkt.inventory  # Adjust to the max available quantity
            messages.warning(request, "Quantity adjusted to max available stock.")  # Optional: Inform the user

        cart = Cart(request)
        cart.add(produkt_id, quantity)

        if request.headers.get('HX-Request') == 'true':  # Check if the request is coming from htmx
            return render(request, 'cart/partials/menu_cart.html')
        else:
            # Redirect to the cart page or wherever you want
            return HttpResponseRedirect(reverse('cart'))
    else:
        # Handle the case for GET request or return an error
        return HttpResponseRedirect(reverse('product_detail', args=(produkt_id,)))


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
                'get_unit_display': produkt.get_unit_display(),
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