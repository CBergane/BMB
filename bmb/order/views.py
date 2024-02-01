import json
import stripe
import logging
logger = logging.getLogger(__name__)

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
            produkt = Produkt.objects.filter(id=item['produkt'].id).select_for_update().first()
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
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid or missing data'}, status=400)

    with transaction.atomic():
        cart = Cart(request)
        total_price = 0
        shipping_cost = 79

        # Skapa ordern först
        order = Order.objects.create(
            user=request.user,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data['phone'],
            address=data['address'],
            zipcode=data['zipcode'],
            city=data['city'],
            paid_amount=0,  # Sätt till 0 tillfälligt
            paid=False
        )

        # Sedan skapa OrderItem för varje artikel i kundvagnen
        for item in cart:
            produkt = Produkt.objects.filter(id=item['produkt_id']).select_for_update().first()
            quantity = int(item['quantity'])
            color_id = item.get('color_id')
            custom_text = item.get('custom_text')
            color = None
            if color_id:
                color = Color.objects.get(id=color_id)
            price = produkt.pris * quantity
            total_price += price  # Uppdatera totalpriset

            OrderItem.objects.create(
                order=order,
                produkt=produkt,
                color=color,
                custom_text=custom_text,
                price=price,
                quantity=quantity
            )

            # Minskning av lager och eventuell avaktivering av produkten
            produkt.inventory -= quantity
            produkt.save()
            if produkt.inventory <= 0:
                produkt.is_active = False
                produkt.save()

        # Uppdatera det totala priset för ordern
        order.paid_amount = total_price + shipping_cost
        order.save()

        cart.clear()

        # Creating a string with order details
        order_details = f"Order ID: {order.id}\n"
        order_details += f"Namn: {order.first_name} {order.last_name}\n"
        order_details += f"Email: {order.email}\n"
        order_details += f"Telefon: {order.phone}\n"
        order_details += f"Address: {order.address}, {order.zipcode}, {order.city}\n"
        order_details += "Beställning:\n"
        for item in order.items.all():
            order_details += f"\tProdukt: {item.produkt.namn}, Färg: {item.color.name if item.color else 'N/A'}, Anpassad text: {item.custom_text if item.custom_text else 'N/A'}, Mängd: {item.quantity}, Pris: {item.price}\n"
        order_details += f"Totalt: {order.paid_amount + shipping_cost}"


        # Email order details to yourself
        send_mail(
            subject=f"Order {order.id} bekräftelse",
            message=order_details,
            from_email='bramycketbattre.best@gmail.com',  # E-postadressen som meddelandet ska skickas från
            recipient_list=['bmb@bramycketbattre.com'],  # Mottagarens e-postadress
            fail_silently=False,
        )

        instructions = """
            Var vänlig betala din order via Swish på följande sätt:
            1. Öppna din Swish app.
            2. Betala till numer: 0766492532.
            3. Summan du skall betala: {} SEK.
            4. Bekräfta att du vill göra din betalning.
            5. Du kommer få ett meddelande att betalningen har skett.

            Har du några frågor så kontakta oss på bmb@bramycketbattre.com.
            """.format(total_price + shipping_cost)

        # Email payment instructions to the customer
        send_mail(
            'Betalnings instruktioner',
            instructions,
            settings.EMAIL_HOST_USER,
            [data['email']],
            fail_silently=False,
        )

    return JsonResponse({'order_id': order.id})
