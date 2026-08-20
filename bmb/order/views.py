import json
import uuid
from datetime import timedelta
from math import ceil

import stripe
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone

from cart.cart import Cart
from products.models import Color, Produkt

from .models import Order, OrderInventoryError, OrderItem


User = get_user_model()


REQUIRED_CUSTOMER_FIELDS = {
    'first_name': 'Förnamn',
    'last_name': 'Efternamn',
    'email': 'E-postadress',
    'phone': 'Telefonnummer',
    'address': 'Adress',
    'zipcode': 'Postnummer',
    'city': 'Stad',
}


def _json_error(message, status=400, field_errors=None):
    payload = {'error': message}

    if field_errors:
        payload['field_errors'] = field_errors

    return JsonResponse(payload, status=status)


def _parse_json_data(request):
    if not request.body:
        return None, _json_error('Begäran saknar JSON-data.', status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return None, _json_error('Ogiltig JSON i begäran.', status=400)

    if not isinstance(data, dict):
        return None, _json_error('JSON-datan måste vara ett objekt.', status=400)

    return data, None


def _parse_customer_data(data):
    cleaned_data = {}
    field_errors = {}

    for field_name, label in REQUIRED_CUSTOMER_FIELDS.items():
        value = data.get(field_name, '')

        if value is None:
            value = ''
        elif not isinstance(value, str):
            value = str(value)

        value = value.strip()
        cleaned_data[field_name] = value

        if not value:
            field_errors[field_name] = f'{label} är obligatoriskt.'

    if field_errors:
        return None, _json_error('Obligatoriska kunduppgifter saknas.', status=400, field_errors=field_errors)

    try:
        validate_email(cleaned_data['email'])
    except ValidationError:
        return None, _json_error(
            'Ogiltig e-postadress.',
            status=400,
            field_errors={'email': 'Ange en giltig e-postadress.'},
        )

    return cleaned_data, None


def _parse_submission_key(data):
    try:
        return uuid.UUID(str(data.get('submission_key'))), None
    except (AttributeError, TypeError, ValueError):
        return None, _json_error('Ogiltig eller saknad ordernyckel.', status=400)


def _build_validated_cart_lines(cart):
    if not cart.cart or len(cart) == 0:
        return None, _json_error('Kundvagnen är tom.', status=400)

    lines = []
    products = {}
    requested_quantities = {}

    for raw_item in cart.cart.values():
        produkt_id = raw_item.get('produkt_id')
        quantity = raw_item.get('quantity')

        try:
            produkt_id = int(produkt_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            return None, _json_error('Kundvagnen innehåller ogiltiga artiklar.', status=400)

        if quantity <= 0:
            return None, _json_error('Kundvagnen innehåller ogiltiga antal.', status=400)

        produkt = products.get(produkt_id)
        if produkt is None:
            produkt = Produkt.objects.filter(pk=produkt_id).first()

            if produkt is None:
                return None, _json_error('En produkt i kundvagnen finns inte längre.', status=400)

            products[produkt_id] = produkt

        color = None
        color_id = raw_item.get('color_id')
        if color_id not in (None, '', 'None'):
            try:
                color_id = int(color_id)
            except (TypeError, ValueError):
                return None, _json_error('Kundvagnen innehåller en ogiltig färgvariant.', status=400)

            color = Color.objects.filter(pk=color_id).first()
            if color is None:
                return None, _json_error('Kundvagnen innehåller en ogiltig färgvariant.', status=400)

        requested_quantities[produkt_id] = requested_quantities.get(produkt_id, 0) + quantity

        lines.append({
            'produkt': produkt,
            'quantity': quantity,
            'color': color,
            'custom_text': raw_item.get('custom_text') or '',
            'line_total': int(produkt.pris * quantity),
        })

    for produkt_id, requested_quantity in requested_quantities.items():
        produkt = products[produkt_id]

        if not produkt.is_active:
            return None, _json_error(f"Produkten '{produkt.namn}' är inte aktiv.", status=409)

        if produkt.inventory < requested_quantity:
            return None, _json_error(f"Otillräckligt lager för '{produkt.namn}'.", status=409)

    total_price = sum(line['line_total'] for line in lines)

    return {
        'lines': lines,
        'total_price': total_price,
    }, None


def start_order(request):
    data, error_response = _parse_json_data(request)
    if error_response:
        return error_response

    data, error_response = _parse_customer_data(data)
    if error_response:
        return error_response

    cart = Cart(request)
    cart_data, error_response = _build_validated_cart_lines(cart)
    if error_response:
        return error_response

    stripe_items = []
    for line in cart_data['lines']:
        produkt = line['produkt']
        stripe_items.append({
            'price_data': {
                'currency': 'sek',
                'product_data': {
                    'name': produkt.namn
                },
                'unit_amount': int(produkt.pris * 100)
            },
            'quantity': line['quantity']
        })

    stripe.api_key = settings.STRIPE_API_KEY_HIDDEN

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=stripe_items,
        mode='payment',
        success_url='https://8000-cbergane-bmb-hwfowlqnoyb.ws-eu103.gitpod.io/cart/success/',
        cancel_url='https://8000-cbergane-bmb-hwfowlqnoyb.ws-eu103.gitpod.io/cart/'
    )
    payment_intent = session.payment_intent

    try:
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                phone=data['phone'],
                address=data['address'],
                zipcode=data['zipcode'],
                city=data['city'],
                payment_intent=payment_intent,
                paid_amount=cart_data['total_price'],
                paid=False,
            )

            for line in cart_data['lines']:
                OrderItem.objects.create(
                    order=order,
                    produkt=line['produkt'],
                    color=line['color'],
                    custom_text=line['custom_text'] or None,
                    price=line['line_total'],
                    quantity=line['quantity'],
                )

            order.mark_as_paid()
            cart.clear()
    except OrderInventoryError as exc:
        return _json_error(str(exc), status=409)

    return JsonResponse({'session': session, 'order': payment_intent})


def _send_swish_order_emails(order_id):
    order = Order.objects.prefetch_related('items__produkt', 'items__color').get(pk=order_id)

    order_details = f"Order ID: {order.id}\n"
    order_details += f"Namn: {order.first_name} {order.last_name}\n"
    order_details += f"Email: {order.email}\n"
    order_details += f"Telefon: {order.phone}\n"
    order_details += f"Address: {order.address}, {order.zipcode}, {order.city}\n"
    order_details += "Beställning:\n"
    for item in order.items.all():
        order_details += f"\tProdukt: {item.produkt.namn}, Färg: {item.color.name if item.color else 'N/A'}, Anpassad text: {item.custom_text if item.custom_text else 'N/A'}, Mängd: {item.quantity}, Pris: {item.price}\n"
    order_details += f"Totalt: {order.paid_amount}"

    send_mail(
        subject=f"Order {order.id} bekräftelse",
        message=order_details,
        from_email='bramycketbattre.best@gmail.com',
        recipient_list=['bmb@bramycketbattre.com'],
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
        """.format(order.paid_amount)

    send_mail(
        'Betalnings instruktioner',
        instructions,
        settings.EMAIL_HOST_USER,
        [order.email],
        fail_silently=False,
    )


def _rate_limit_response(retry_after):
    response = _json_error(
        'För många nya obetalda Swish-ordrar. Försök igen senare.',
        status=429,
    )
    response['Retry-After'] = str(retry_after)
    return response


def start_swish_order(request):
    if request.method != 'POST':
        return _json_error('Endast POST är tillåtet.', status=405)

    if not request.user.is_authenticated:
        return _json_error('Du måste vara inloggad för att skapa en Swish-order.', status=401)

    if not request.user.is_active:
        return _json_error('Ditt konto måste vara aktivt för att skapa en Swish-order.', status=403)

    data, error_response = _parse_json_data(request)
    if error_response:
        return error_response

    submission_key, error_response = _parse_submission_key(data)
    if error_response:
        return error_response

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=request.user.pk)
        existing_order = Order.objects.filter(submission_key=submission_key).first()

        if existing_order:
            if existing_order.user_id != locked_user.pk:
                return _json_error('Ogiltig ordernyckel.', status=403)

            return JsonResponse({'order_id': existing_order.id})

        customer_data, error_response = _parse_customer_data(data)
        if error_response:
            return error_response

        cart = Cart(request)
        cart_data, error_response = _build_validated_cart_lines(cart)
        if error_response:
            return error_response

        now = timezone.now()
        window_seconds = max(1, settings.SWISH_ORDER_PENDING_WINDOW_SECONDS)
        pending_limit = max(1, settings.SWISH_ORDER_PENDING_LIMIT)
        window_start = now - timedelta(seconds=window_seconds)
        pending_orders = list(
            Order.objects.filter(
                user=locked_user,
                paid=False,
                created_at__gte=window_start,
            ).only('created_at').order_by('created_at')
        )

        if len(pending_orders) >= pending_limit:
            retry_at = pending_orders[0].created_at + timedelta(seconds=window_seconds)
            retry_after = max(1, ceil((retry_at - now).total_seconds()))
            return _rate_limit_response(retry_after)

        shipping_cost = 79
        grand_total = cart_data['total_price'] + shipping_cost

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=locked_user,
                    first_name=customer_data['first_name'],
                    last_name=customer_data['last_name'],
                    email=customer_data['email'],
                    phone=customer_data['phone'],
                    address=customer_data['address'],
                    zipcode=customer_data['zipcode'],
                    city=customer_data['city'],
                    paid_amount=grand_total,
                    paid=False,
                    submission_key=submission_key,
                )

                for line in cart_data['lines']:
                    OrderItem.objects.create(
                        order=order,
                        produkt=line['produkt'],
                        color=line['color'],
                        custom_text=line['custom_text'] or None,
                        price=line['line_total'],
                        quantity=line['quantity'],
                    )
        except IntegrityError:
            existing_order = Order.objects.filter(submission_key=submission_key).first()
            if existing_order and existing_order.user_id == locked_user.pk:
                return JsonResponse({'order_id': existing_order.id})
            return _json_error('Ogiltig ordernyckel.', status=403)

        cart.clear()
        transaction.on_commit(lambda order_id=order.id: _send_swish_order_emails(order_id))

    return JsonResponse({'order_id': order.id})
