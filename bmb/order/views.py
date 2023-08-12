import json
import stripe

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect

from cart.cart import Cart

from .models import Order, OrderItem

def start_order(request):
    cart = Cart(request)
    data = json.loads(request.body)
    total_price = 0

    items = []

    for item in cart:
        produkt = item['produkt']
        total_price += produkt.pris * int(item['quantity'])

        obj = {
            'price_data': {
                'currency': 'sek',
                'product_data': {
                    'name': produkt.namn
                },
                'unit_amount': int(produkt.pris * 100)
            },
            'quantity': item['quantity']
        }

        items.append(obj)


    stripe.api_key = settings.STRIPE_API_KEY_HIDDEN

    session = stripe.checkout.Session.create(
        payment_method_types = ['card'],
        line_items = items,
        mode = 'payment',
        success_url = 'https://8000-cbergane-bmb-hwfowlqnoyb.ws-eu103.gitpod.io/cart/succsess/',
        cancel_url = 'https://8000-cbergane-bmb-hwfowlqnoyb.ws-eu103.gitpod.io/cart/'
    )
    payment_intent = session.payment_intent

    first_name = data['first_name']
    last_name = data['last_name']
    email = data['email']
    address = data['address']
    zipcode = data['zipcode']
    city = data['city']
    phone = data['phone']

    order = Order.objects.create(user=request.user, first_name=first_name, last_name=last_name, email=email, phone=phone, address=address, zipcode=zipcode, city=city)
    order.payment_intent = payment_intent
    order.paid_amount = total_price
    order.paid = True
    order.save()

    for item in cart:
        produkt = item['produkt']
        quantity = int(item['quantity'])
        price = produkt.pris * quantity
        item = OrderItem.objects.create(order=order, produkt=produkt, price=price, quantity=quantity)

    return JsonResponse({'session': session, 'order': payment_intent})