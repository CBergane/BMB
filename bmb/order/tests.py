import json
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from order.models import Order, OrderInventoryError, OrderItem
from products.models import Category, Produkt


User = get_user_model()


class SwishOrderHardeningTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='kund',
            email='kund@example.com',
            password='hemligt123',
            first_name='Kund',
            last_name='Testsson',
        )
        self.category = Category.objects.create(namn='Tyger')
        self.other_user = User.objects.create_user(
            username='annan-kund',
            email='annan@example.com',
            password='hemligt123',
        )
        self.product = Produkt.objects.create(
            category=self.category,
            namn='Bomullstyg',
            inventory=5,
            pris=Decimal('100.00'),
            is_active=True,
            publication_status=Produkt.PublicationStatus.PUBLISHED,
        )
        self.second_product = Produkt.objects.create(
            category=self.category,
            namn='Linnetyg',
            inventory=3,
            pris=Decimal('150.00'),
            is_active=True,
            publication_status=Produkt.PublicationStatus.PUBLISHED,
        )
        self.url = reverse('start_swish_order')

    def _payload(self, **overrides):
        payload = {
            'first_name': 'Anna',
            'last_name': 'Andersson',
            'email': 'anna@example.com',
            'phone': '0701234567',
            'address': 'Testgatan 1',
            'zipcode': '12345',
            'city': 'Stockholm',
            'submission_key': str(uuid.uuid4()),
        }
        payload.update(overrides)
        return payload

    def _set_cart(self, *entries):
        session = self.client.session
        cart = {}

        for entry in entries:
            product = entry['product']
            quantity = entry['quantity']
            color_id = entry.get('color_id')
            custom_text = entry.get('custom_text', '')
            cart_key = f"{product.id}_{color_id}_{custom_text}"
            cart[cart_key] = {
                'produkt_id': product.id,
                'color_id': color_id,
                'custom_text': custom_text,
                'quantity': quantity,
            }

        session[settings.CART_SESSION_ID] = cart
        session.save()

    def _create_unpaid_order(self, *items, user=None, submission_key=None, paid=False):
        order = Order.objects.create(
            user=user or self.user,
            first_name='Anna',
            last_name='Andersson',
            email='anna@example.com',
            phone='0701234567',
            address='Testgatan 1',
            zipcode='12345',
            city='Stockholm',
            paid_amount=0,
            paid=paid,
            submission_key=submission_key,
        )

        total_price = 0
        for product, quantity in items:
            line_total = int(product.pris * quantity)
            total_price += line_total
            OrderItem.objects.create(
                order=order,
                produkt=product,
                price=line_total,
                quantity=quantity,
            )

        order.paid_amount = total_price
        order.save(update_fields=['paid_amount'])
        return order

    def test_anonymous_user_is_denied(self):
        self._set_cart({'product': self.product, 'quantity': 1})

        response = self.client.post(
            self.url,
            data=json.dumps(self._payload()),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Order.objects.count(), 0)

    def test_get_request_is_denied(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Order.objects.count(), 0)

    def test_empty_cart_is_denied(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            data=json.dumps(self._payload()),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Kundvagnen är tom.')
        self.assertEqual(Order.objects.count(), 0)

    def test_insufficient_inventory_is_denied(self):
        self.client.force_login(self.user)
        self._set_cart({'product': self.product, 'quantity': 6})

        response = self.client.post(
            self.url,
            data=json.dumps(self._payload()),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn('Otillräckligt lager', response.json()['error'])
        self.assertEqual(Order.objects.count(), 0)

    @patch('order.views.send_mail')
    def test_unpublished_product_in_saved_cart_cannot_create_order(self, send_mail_mock):
        self.client.force_login(self.user)

        for status in (
            Produkt.PublicationStatus.DRAFT,
            Produkt.PublicationStatus.ARCHIVED,
        ):
            with self.subTest(status=status):
                self.product.publication_status = status
                self.product.save(update_fields=['publication_status'])
                self._set_cart({'product': self.product, 'quantity': 2})

                response = self.client.post(
                    self.url,
                    data=json.dumps(self._payload()),
                    content_type='application/json',
                )

                self.assertEqual(response.status_code, 409)
                self.assertIn('inte längre publicerad eller tillgänglig', response.json()['error'])
                self.assertEqual(Order.objects.count(), 0)
                self.assertEqual(OrderItem.objects.count(), 0)
                self.product.refresh_from_db()
                self.assertEqual(self.product.inventory, 5)

        self.assertEqual(send_mail_mock.call_count, 0)

    @patch('order.views.send_mail')
    def test_unpaid_order_does_not_change_inventory(self, send_mail_mock):
        self.client.force_login(self.user)
        self._set_cart({'product': self.product, 'quantity': 2})

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                self.url,
                data=json.dumps(self._payload()),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()

        order = Order.objects.get()
        self.assertFalse(order.paid)
        self.assertEqual(self.product.inventory, 5)
        self.assertEqual(send_mail_mock.call_count, 2)

    @patch('order.views.send_mail')
    def test_same_submission_key_reuses_order_without_duplicate_rows_or_email(self, send_mail_mock):
        self.client.force_login(self.user)
        submission_key = str(uuid.uuid4())
        payload = self._payload(submission_key=submission_key)
        self._set_cart({'product': self.product, 'quantity': 2})

        with self.captureOnCommitCallbacks(execute=True):
            first_response = self.client.post(
                self.url,
                data=json.dumps(payload),
                content_type='application/json',
            )
        second_response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(first_response.json()['order_id'], second_response.json()['order_id'])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        self.assertEqual(send_mail_mock.call_count, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 5)

    @patch('order.views.send_mail')
    def test_new_submission_key_creates_new_pending_order_within_limit(self, send_mail_mock):
        self.client.force_login(self.user)

        self._set_cart({'product': self.product, 'quantity': 1})
        with self.captureOnCommitCallbacks(execute=True):
            first_response = self.client.post(
                self.url,
                data=json.dumps(self._payload()),
                content_type='application/json',
            )

        self._set_cart({'product': self.product, 'quantity': 1})
        with self.captureOnCommitCallbacks(execute=True):
            second_response = self.client.post(
                self.url,
                data=json.dumps(self._payload()),
                content_type='application/json',
            )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertNotEqual(first_response.json()['order_id'], second_response.json()['order_id'])
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(send_mail_mock.call_count, 4)
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 5)

    @override_settings(SWISH_ORDER_PENDING_LIMIT=3, SWISH_ORDER_PENDING_WINDOW_SECONDS=15 * 60)
    def test_fourth_pending_order_is_rate_limited(self):
        for _ in range(3):
            self._create_unpaid_order((self.product, 1), submission_key=uuid.uuid4())

        self.client.force_login(self.user)
        self._set_cart({'product': self.product, 'quantity': 1})
        response = self.client.post(
            self.url,
            data=json.dumps(self._payload()),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 429)
        self.assertIn('För många nya obetalda Swish-ordrar', response.json()['error'])
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertEqual(Order.objects.count(), 3)
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 5)

    @override_settings(SWISH_ORDER_PENDING_LIMIT=3, SWISH_ORDER_PENDING_WINDOW_SECONDS=15 * 60)
    @patch('order.views.send_mail')
    def test_paid_and_old_orders_do_not_count_toward_rate_limit(self, send_mail_mock):
        self._create_unpaid_order((self.product, 1), submission_key=uuid.uuid4())
        self._create_unpaid_order((self.product, 1), submission_key=uuid.uuid4())
        self._create_unpaid_order((self.product, 1), submission_key=uuid.uuid4(), paid=True)
        old_order = self._create_unpaid_order((self.product, 1), submission_key=uuid.uuid4())
        Order.objects.filter(pk=old_order.pk).update(created_at=timezone.now() - timedelta(minutes=16))

        self.client.force_login(self.user)
        self._set_cart({'product': self.product, 'quantity': 1})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                self.url,
                data=json.dumps(self._payload()),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 5)
        self.assertEqual(send_mail_mock.call_count, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 5)

    @patch('order.views.send_mail')
    def test_submission_key_owned_by_another_user_is_denied(self, send_mail_mock):
        submission_key = uuid.uuid4()
        self._create_unpaid_order(
            (self.product, 1),
            user=self.other_user,
            submission_key=submission_key,
        )
        self.client.force_login(self.user)
        self._set_cart({'product': self.product, 'quantity': 1})

        response = self.client.post(
            self.url,
            data=json.dumps(self._payload(submission_key=str(submission_key))),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Ogiltig ordernyckel.')
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(send_mail_mock.call_count, 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 5)

    def test_marking_paid_decreases_inventory_exactly_once(self):
        order = self._create_unpaid_order((self.product, 2))

        changed = order.mark_as_paid()

        self.assertTrue(changed)
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(self.product.inventory, 3)

    def test_second_payment_attempt_does_not_decrease_inventory_again(self):
        order = self._create_unpaid_order((self.product, 2))

        first_change = order.mark_as_paid()
        second_change = order.mark_as_paid()

        self.assertTrue(first_change)
        self.assertFalse(second_change)
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 3)

    def test_inventory_changes_roll_back_when_stock_is_insufficient(self):
        order = self._create_unpaid_order((self.product, 2), (self.second_product, 4))

        with self.assertRaises(OrderInventoryError):
            order.mark_as_paid()

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.second_product.refresh_from_db()

        self.assertFalse(order.paid)
        self.assertEqual(self.product.inventory, 5)
        self.assertEqual(self.second_product.inventory, 3)

    def test_mark_as_paid_uses_current_database_status(self):
        order = self._create_unpaid_order((self.product, 2))
        stale_order = Order.objects.get(pk=order.pk)

        first_change = order.mark_as_paid()
        second_change = stale_order.mark_as_paid()

        self.assertTrue(first_change)
        self.assertFalse(second_change)

        stale_order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertTrue(stale_order.paid)
        self.assertEqual(self.product.inventory, 3)


class OrderAdminPaymentFlowTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='hemligt123',
        )
        self.customer = User.objects.create_user(
            username='kund',
            email='kund@example.com',
            password='hemligt123',
        )
        self.category = Category.objects.create(namn='Tyger')
        self.product = Produkt.objects.create(
            category=self.category,
            namn='Adminbomull',
            inventory=8,
            pris=Decimal('120.00'),
            is_active=True,
            publication_status=Produkt.PublicationStatus.PUBLISHED,
        )

    def _create_unpaid_order(self, quantity=2):
        order = Order.objects.create(
            user=self.customer,
            first_name='Anna',
            last_name='Andersson',
            email='anna@example.com',
            phone='0701234567',
            address='Testgatan 1',
            zipcode='12345',
            city='Stockholm',
            paid_amount=int(self.product.pris * quantity),
            paid=False,
        )
        OrderItem.objects.create(
            order=order,
            produkt=self.product,
            price=int(self.product.pris * quantity),
            quantity=quantity,
        )
        return order

    def _build_admin_change_payload(self, order, mark_paid=None, **overrides):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin:order_order_change', args=[order.pk]))
        self.assertEqual(response.status_code, 200)

        inline_formset = response.context['inline_admin_formsets'][0].formset
        prefix = inline_formset.prefix

        order.refresh_from_db()
        items = list(order.items.order_by('pk'))

        payload = {
            'user': str(order.user_id or ''),
            'first_name': order.first_name,
            'last_name': order.last_name,
            'email': order.email,
            'address': order.address,
            'zipcode': order.zipcode,
            'city': order.city,
            'phone': order.phone,
            'payment_intent': order.payment_intent or '',
            'paid_amount': str(order.paid_amount or ''),
            'status': order.status,
            '_save': 'Save',
            f'{prefix}-TOTAL_FORMS': str(len(items)),
            f'{prefix}-INITIAL_FORMS': str(len(items)),
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '1000',
        }

        if mark_paid is None:
            if order.paid:
                payload['paid'] = 'on'
        elif mark_paid:
            payload['paid'] = 'on'

        for index, item in enumerate(items):
            payload[f'{prefix}-{index}-id'] = str(item.pk)
            payload[f'{prefix}-{index}-order'] = str(order.pk)
            payload[f'{prefix}-{index}-produkt'] = str(item.produkt_id)
            payload[f'{prefix}-{index}-color'] = str(item.color_id or '')
            payload[f'{prefix}-{index}-custom_text'] = item.custom_text or ''
            payload[f'{prefix}-{index}-price'] = str(item.price)
            payload[f'{prefix}-{index}-quantity'] = str(item.quantity)

        payload.update(overrides)
        return payload

    def test_admin_change_view_marks_paid_and_later_edit_does_not_reduce_inventory_again(self):
        order = self._create_unpaid_order(quantity=2)

        first_payload = self._build_admin_change_payload(order, mark_paid=True)
        first_response = self.client.post(
            reverse('admin:order_order_change', args=[order.pk]),
            data=first_payload,
            follow=True,
        )

        self.assertEqual(first_response.status_code, 200)
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(self.product.inventory, 6)

        second_payload = self._build_admin_change_payload(order, address='Ny adress 2')
        second_response = self.client.post(
            reverse('admin:order_order_change', args=[order.pk]),
            data=second_payload,
            follow=True,
        )

        self.assertEqual(second_response.status_code, 200)
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.address, 'Ny adress 2')
        self.assertTrue(order.paid)
        self.assertEqual(self.product.inventory, 6)

    def test_admin_change_view_keeps_paid_false_when_inventory_update_fails(self):
        order = self._create_unpaid_order(quantity=2)
        self.product.inventory = 1
        self.product.save(update_fields=['inventory'])

        payload = self._build_admin_change_payload(order, mark_paid=True)
        response = self.client.post(
            reverse('admin:order_order_change', args=[order.pk]),
            data=payload,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertFalse(order.paid)
        self.assertEqual(self.product.inventory, 1)

        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertTrue(any('Lageruppdateringen kunde inte genomföras' in message for message in messages))
