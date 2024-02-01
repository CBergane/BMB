from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
import logging
logger = logging.getLogger(__name__)

from .cart import Cart
from django.shortcuts import get_object_or_404, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from products.models import Produkt, Color

def add_to_cart(request, produkt_id):
    produkt = get_object_or_404(Produkt, pk=produkt_id)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        color_id = request.POST.get('color_id', None)
        custom_text = request.POST.get('custom_text', '')

        if quantity > produkt.inventory:
            quantity = produkt.inventory
            messages.warning(request, "Du har överskridit maximalt antal enheter i lagret.")

        cart = Cart(request)
        cart.add(produkt_id, quantity, color_id=color_id, custom_text=custom_text)

        if request.headers.get('HX-Request') == 'true':
            return render(request, 'cart/partials/menu_cart.html')
        else:
            return HttpResponseRedirect(reverse('cart'))
    else:
        return HttpResponseRedirect(reverse('product_detail', args=(produkt_id,)))


def cart(request):
    return render(request, 'cart/cart.html')

def success(request):
    return render(request, 'cart/success.html')

def update_cart(request, cart_key, action):
    logger.info(f"Uppdaterar varukorg: cart_key={cart_key}, action={action}")
    cart = Cart(request)

    if action == 'increment':
        cart.increment_item(cart_key)
    elif action == 'decrement':
        cart.decrement_item(cart_key)

    item = cart.get_item(cart_key)
    if item:
        # Hämta uppdaterad information
        response = render(request, 'cart/partials/cart_item.html', {'item': item})
    else:
        response = HttpResponse("Item not found", status=404)

    response['HX-Trigger'] = 'update-menu-cart'
    return response

def update_cart_quantity(request, cart_key, action):
    cart = Cart(request)
    if action == 'increment':
        cart.increment_item(cart_key)
    elif action == 'decrement':
        cart.decrement_item(cart_key)
    
    item = cart.get_item(cart_key)
    if item:
        return JsonResponse({'quantity': item['quantity']})
    else:
        return JsonResponse({'error': 'Item not found'}, status=404)

def clear_cart(request):
    cart = Cart(request)
    cart.clear()
    return redirect('cart')

@login_required
def checkout(request):
    pub_key = settings.STRIPE_API_KEY_PUBLISHABLE
    return render(request, 'cart/checkout.html', {'pub_key': pub_key})

def hx_menu_cart(request):
    return render(request, 'cart/partials/menu_cart.html')

def hx_cart_total(request):
    return render(request, 'cart/partials/cart_total.html')