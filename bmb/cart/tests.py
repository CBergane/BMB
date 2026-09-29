from html.parser import HTMLParser
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from order.models import Order
from products.models import Category, Produkt


class CheckoutInputs(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.values = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('id', '').startswith('checkout-'):
            self.values[attrs['name']] = attrs.get('value', '')


class CheckoutPrefillTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username='checkout-profile',
            first_name='Anna',
            last_name='Andersson',
            email='anna@example.com',
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('checkout')
        self.submitted = {
            'first_name': 'Lisa',
            'last_name': "O'Neill",
            'email': 'lisa@example.com',
            'address': 'Testgatan 2',
            'zipcode': '12345',
            'city': 'Stockholm',
            'phone': '0701234567',
        }

    def values(self, response):
        self.assertEqual(response.status_code, 200)
        return CheckoutInputs(response.content.decode()).values

    def test_authenticated_first_name_prefill(self):
        self.assertEqual(self.values(self.client.get(self.url))['first_name'], 'Anna')

    def test_authenticated_last_name_prefill(self):
        self.assertEqual(self.values(self.client.get(self.url))['last_name'], 'Andersson')

    def test_authenticated_email_prefill(self):
        self.assertEqual(self.values(self.client.get(self.url))['email'], 'anna@example.com')

    def test_other_checkout_fields_start_empty(self):
        values = self.values(self.client.get(self.url))
        for field in ('address', 'zipcode', 'city', 'phone'):
            self.assertEqual(values[field], '')

    def test_submitted_values_take_precedence_over_profile_defaults(self):
        response = self.client.post(self.url, self.submitted)

        self.assertEqual(self.values(response), self.submitted)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Anna')
        self.assertEqual(self.user.last_name, 'Andersson')
        self.assertEqual(self.user.email, 'anna@example.com')

    def test_blank_or_omitted_posted_values_do_not_restore_profile_defaults(self):
        for data in ({}, {field: '' for field in self.submitted}):
            with self.subTest(data=data):
                response = self.client.post(self.url, data)

                self.assertEqual(self.values(response), {field: '' for field in self.submitted})

    def test_posted_values_are_preserved_when_redisplaying_after_validation_error(self):
        data = {**self.submitted, 'email': 'invalid-email', 'submission_key': str(uuid4())}
        error = self.client.post(reverse('start_swish_order'), data, content_type='application/json')
        self.assertEqual(error.status_code, 400)
        self.assertIn('email', error.json()['field_errors'])
        self.assertFalse(Order.objects.exists())

        response = self.client.post(self.url, data)

        self.assertEqual(self.values(response), {**self.submitted, 'email': 'invalid-email'})

    def test_order_uses_manually_entered_values_instead_of_profile(self):
        category = Category.objects.create(namn='Tyg')
        product = Produkt.objects.create(
            category=category, namn='Bomull', pris='100.00', inventory=10,
            publication_status=Produkt.PublicationStatus.PUBLISHED,
        )
        session = self.client.session
        session[settings.CART_SESSION_ID] = {
            f'{product.pk}_None_': {
                'produkt_id': product.pk, 'quantity': 1, 'color_id': None, 'custom_text': '',
            },
        }
        session.save()

        response = self.client.post(
            reverse('start_swish_order'),
            {**self.submitted, 'submission_key': str(uuid4())},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(pk=response.json()['order_id'])
        for field, value in self.submitted.items():
            self.assertEqual(getattr(order, field), value)

    def test_posted_values_remain_html_escaped(self):
        data = {**self.submitted, 'last_name': '\"><script>alert(1)</script>'}

        response = self.client.post(self.url, data)

        self.assertEqual(self.values(response)['last_name'], data['last_name'])
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_anonymous_get_and_post_still_redirect_to_login(self):
        self.client.logout()
        for method in ('get', 'post'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    self.url, self.submitted if method == 'post' else {},
                )

                self.assertRedirects(
                    response, f'{reverse("login")}?next={self.url}',
                    fetch_redirect_response=False,
                )
                self.assertNotIn('anna@example.com', response.content.decode())
