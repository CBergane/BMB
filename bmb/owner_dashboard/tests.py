from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from order.models import Order
from products.models import Category, Produkt


User = get_user_model()


class OwnerDashboardAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.regular_user = User.objects.create_user(
            username='kund',
            password='hemligt123',
        )
        cls.staff_user = User.objects.create_user(
            username='personal',
            password='hemligt123',
            is_staff=True,
        )
        cls.inactive_superuser = User.objects.create_superuser(
            username='inaktiv-agare',
            email='inaktiv@example.com',
            password='hemligt123',
        )
        cls.inactive_superuser.is_active = False
        cls.inactive_superuser.save(update_fields=['is_active'])
        cls.superuser = User.objects.create_superuser(
            username='agare',
            email='agare@example.com',
            password='hemligt123',
        )
        cls.url = reverse('owner_dashboard:dashboard')

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={self.url}',
            fetch_redirect_response=False,
        )

    def test_regular_user_gets_forbidden(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_staff_user_without_superuser_gets_forbidden(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_inactive_superuser_is_denied(self):
        self.client.force_login(self.inactive_superuser)

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={self.url}',
            fetch_redirect_response=False,
        )

    def test_active_superuser_gets_dashboard_with_security_headers(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ägarpanel')
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">', html=True)
        self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')
        self.assertIn('no-cache', response['Cache-Control'])

    def test_direct_owner_url_cannot_bypass_access_control(self):
        self.client.force_login(self.regular_user)

        response = self.client.get('/owner/')

        self.assertEqual(response.status_code, 403)

    def test_navigation_link_is_only_visible_to_active_superuser(self):
        self.client.force_login(self.regular_user)
        regular_response = self.client.get(reverse('myaccount'))

        self.client.force_login(self.superuser)
        superuser_response = self.client.get(reverse('myaccount'))

        self.assertNotContains(regular_response, self.url)
        self.assertContains(superuser_response, self.url)


class OwnerDashboardStatisticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username='agare',
            email='agare@example.com',
            password='hemligt123',
        )
        category = Category.objects.create(namn='Dashboardprodukter')
        Produkt.objects.create(
            category=category,
            namn='Aktiv produkt',
            inventory=12,
            is_active=True,
            pris=Decimal('100.00'),
        )
        Produkt.objects.create(
            category=category,
            namn='Lågt lager',
            inventory=5,
            is_active=True,
            pris=Decimal('120.00'),
        )
        Produkt.objects.create(
            category=category,
            namn='Slut i lager',
            inventory=0,
            is_active=False,
            pris=Decimal('140.00'),
        )

        cls.latest_order = cls._create_order('Senaste', paid=False, paid_amount=299)
        cls._create_order('Betald', paid=True, paid_amount=199)
        cls._create_order('Obetald', paid=False, paid_amount=99)

    @classmethod
    def _create_order(cls, first_name, paid, paid_amount):
        return Order.objects.create(
            user=cls.superuser,
            first_name=first_name,
            last_name='Kund',
            email='kund@example.com',
            phone='0701234567',
            address='Testgatan 1',
            zipcode='12345',
            city='Stockholm',
            paid=paid,
            paid_amount=paid_amount,
        )

    def test_dashboard_shows_correct_product_and_order_totals(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse('owner_dashboard:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['product_totals'], {
            'total': 3,
            'active': 2,
            'low_stock': 2,
        })
        self.assertEqual(response.context['order_totals'], {
            'total': 3,
            'unpaid': 2,
        })
        self.assertContains(response, 'Senaste ordrarna')
        self.assertContains(response, 'Senaste Kund')
