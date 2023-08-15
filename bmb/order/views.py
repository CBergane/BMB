import json
import stripe

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.core.mail import send_mail

from cart.cart import Cart

from .models import Order, OrderItem
from products.models import Produkt

def start_order(request):
    with transaction.atomic():
        cart = Cart(request)
        data = json.loads(request.body)
        total_price = 0
        items = []

        for item in cart:
            produkt = item['produkt']
            quantity = int(item['quantity'])

            # Validate that enough inventory is available
            if produkt.inventory < quantity:
                return JsonResponse({'error': f"Only {produkt.inventory} {produkt.namn} available in stock."}, status=400)

            total_price += produkt.pris * quantity

            items.append({
                'price_data': {
                    'currency': 'sek',
                    'product_data': {
                        'name': produkt.namn
                    },
                    'unit_amount': int(produkt.pris * 100)
                },
                'quantity': item['quantity']
            })


        stripe.api_key = settings.STRIPE_API_KEY_HIDDEN

        session = stripe.checkout.Session.create(
            payment_method_types = ['card'],
            line_items = items,
            mode = 'payment',
            success_url = 'https://8000-cbergane-bmb-hwfowlqnoyb.ws-eu103.gitpod.io/cart/success/',
            cancel_url = 'https://8000-cbergane-bmb-hwfowlqnoyb.ws-eu103.gitpod.io/cart/'
        )
        payment_intent = session.payment_intent

        order = Order.objects.create(
            user=request.user, 
            first_name=data['first_name'], 
            last_name=data['last_name'], 
            email=data['email'], 
            phone=data['phone'], 
            address=data['address'], 
            zipcode=data['zipcode'], 
            city=data['city'],
            payment_intent=payment_intent,
            paid_amount=total_price,
            paid=True
            )

        for item in cart:
            produkt = item['produkt'].select_for_update()  # Lock the product row
            quantity = int(item['quantity'])
            price = produkt.pris * quantity
            item = OrderItem.objects.create(order=order, produkt=produkt, price=price, quantity=quantity)

            # Decrement the inventory for the purchased product
            produkt.inventory -= quantity
            produkt.save()

            # Check if inventory reaches 0 and deactivate the product if needed
            if produkt.inventory <= 0:
                produkt.is_active = False
                produkt.save()

        cart.clear()

    return JsonResponse({'session': session, 'order': payment_intent})


def start_swish_order(request):
    with transaction.atomic():
        cart = Cart(request)
        data = json.loads(request.body)
        total_price = 0

        for item in cart:
            produkt = item['produkt']
            quantity = int(item['quantity'])

            # Validate that enough inventory is available
            if produkt.inventory < quantity:
                return JsonResponse({'error': f"Only {produkt.inventory} {produkt.namn} available in stock."}, status=400)

            total_price += produkt.pris * quantity

        # Create the order in your database
        order = Order.objects.create(
            user=request.user,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data['phone'],
            address=data['address'],
            zipcode=data['zipcode'],
            city=data['city'],
            paid_amount=total_price,
            paid=False
        )

        # Creating OrderItems
        for item in cart:
            produkt = item['produkt'].select_for_update()  # Lock the product row
            quantity = int(item['quantity'])
            price = produkt.pris * quantity
            item = OrderItem.objects.create(order=order, produkt=produkt, price=price, quantity=quantity)

            # Decrement the inventory for the purchased product
            produkt.inventory -= quantity
            produkt.save()

            # Check if inventory reaches 0 and deactivate the product if needed
            if produkt.inventory <= 0:
                produkt.is_active = False
                produkt.save()

        cart.clear()

        # Creating a string with order details
        order_details = f"Order ID: {order.id}\n"
        order_details += f"Name: {order.first_name} {order.last_name}\n"
        order_details += f"Email: {order.email}\n"
        order_details += f"Phone: {order.phone}\n"
        order_details += f"Address: {order.address}, {order.zipcode}, {order.city}\n"
        order_details += "Items:\n"
        for item in order.items.all():
            order_details += f"\tProduct: {item.produkt.namn}, Quantity: {item.quantity}, Price: {item.price}\n"
        order_details += f"Total Amount: {order.paid_amount}"

        # Email order details to yourself
        send_mail(
            'New Swish Order Received',
            order_details,  # This contains the order details
            settings.EMAIL_HOST_USER,
            ['christian.bergane@gmail.com'],
            fail_silently=False,
        )

        instructions = """
            Please make your payment using Swish by following these instructions:
            1. Öppna din Swish app.
            2. Betala till numer: 123-456-789.
            3. Summan du skall betala: {} SEK.
            4. Bekräfta din att du vill göra din betalning.
            5. Du kommer få ett meddelande att betalningen har skett.

            Har du några frågor så kontakta oss på support@example.com.
            """.format(total_price)

        # Email payment instructions to the customer
        send_mail(
            'Payment Instructions',
            instructions,
            settings.EMAIL_HOST_USER,
            [data['email']],
            fail_silently=False,
        )

    return JsonResponse({'order_id': order.id})
