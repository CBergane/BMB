from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Meddelande
from core.templatetags.price_filters import sek
from order.models import Order, OrderItem
from products.models import Category, Produkt


User = get_user_model()


class SekPriceFilterTests(SimpleTestCase):
    def test_sek_formats_supported_values_with_swedish_decimal_comma(self):
        cases = (
            (Decimal('9.834'), '9,83 kr'),
            (14.9, '14,90 kr'),
            (152, '152,00 kr'),
            (None, '0,00 kr'),
        )

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(sek(value), expected)

    def test_sek_uses_round_half_up(self):
        self.assertEqual(sek(Decimal('9.835')), '9,84 kr')


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class GotsEmbedTests(SimpleTestCase):
    def test_video_uses_privacy_enhanced_embed(self):
        rendered_template = render_to_string(
            "core/frontpage.html",
            {"meddelanden": [], "produkter": []},
        )

        self.assertIn(
            'src="https://www.youtube-nocookie.com/embed/xhQiGhnbDqw"',
            rendered_template,
        )
        self.assertIn(
            'referrerpolicy="strict-origin-when-cross-origin"',
            rendered_template,
        )


class PublicStorefrontSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.parent_category = Category.objects.create(namn="Tyger")
        cls.child_category = Category.objects.create(
            namn="Bomull",
            parent=cls.parent_category,
        )
        cls.product = Produkt.objects.create(
            category=cls.child_category,
            namn="Nordisk bomull",
            unit="dm",
            is_fabric=True,
            is_stubbie=False,
            is_bmb_exclusive=True,
            length=Decimal("12.00"),
            inventory=10,
            is_active=True,
            publication_status=Produkt.PublicationStatus.PUBLISHED,
            pris=Decimal("149.00"),
            discount_percentage=10,
            beskrivning="Mjuk bomull som passar flera typer av projekt.",
        )
        Meddelande.objects.create(
            text="Nya leveranser varje vecka.",
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            is_active=True,
        )
        cls.user = User.objects.create_user(
            username='checkout-kund',
            password='hemligt123',
        )

    def test_public_pages_render(self):
        urls = [
            reverse("frontpage"),
            reverse("news"),
            reverse("discounted_products"),
            reverse("stubbies"),
            reverse("bmb_exclusive_products"),
            reverse("signup"),
            reverse("login"),
            reverse("cart"),
            reverse("admin:login"),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_shop_renders_with_selected_category(self):
        response = self.client.get(
            reverse("shop"),
            {"category": self.child_category.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.namn)
        self.assertContains(response, '134,10 kr')

    def test_product_detail_renders(self):
        response = self.client.get(
            reverse("produkt", kwargs={"slug": self.product.slug}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.namn)
        self.assertContains(response, '134,10 kr')

    def test_cart_and_checkout_render_formatted_sek_values(self):
        cart_response = self.client.get(reverse('cart'))
        self.assertEqual(cart_response.status_code, 200)
        self.assertContains(cart_response, '0,00 kr')
        self.assertContains(cart_response, '79,00 kr')

        self.client.force_login(self.user)
        checkout_response = self.client.get(reverse('checkout'))
        self.assertEqual(checkout_response.status_code, 200)
        self.assertContains(checkout_response, '0,00 kr')
        self.assertContains(checkout_response, '79,00 kr')


class MyAccountOrderSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user(
            username='orderkund',
            email='orderkund@example.com',
            password='hemligt123',
            first_name='Anna',
            last_name='Andersson',
        )
        cls.other_customer = User.objects.create_user(
            username='annan-orderkund',
            email='annan@example.com',
            password='hemligt123',
        )
        cls.staff_user = User.objects.create_user(
            username='orderpersonal',
            password='hemligt123',
            is_staff=True,
        )
        cls.superuser = User.objects.create_superuser(
            username='orderadmin',
            email='orderadmin@example.com',
            password='hemligt123',
        )
        cls.empty_customer = User.objects.create_user(
            username='orderlos',
            password='hemligt123',
        )
        cls.inactive_customer = User.objects.create_user(
            username='inaktiv-orderkund',
            password='hemligt123',
            is_active=False,
        )
        category = Category.objects.create(namn='Orderhistorik')
        cls.own_product = Produkt.objects.create(
            category=category,
            namn='Egen historisk produkt',
            inventory=10,
            is_active=True,
            publication_status=Produkt.PublicationStatus.PUBLISHED,
            pris=Decimal('125.00'),
        )
        cls.other_product = Produkt.objects.create(
            category=category,
            namn='Annan kunds hemliga produkt',
            inventory=10,
            is_active=True,
            publication_status=Produkt.PublicationStatus.PUBLISHED,
            pris=Decimal('333.00'),
        )
        cls.older_order = cls._create_order(
            cls.customer,
            first_name='Anna',
            status=Order.Status.RECEIVED,
            paid=False,
        )
        OrderItem.objects.create(
            order=cls.older_order,
            produkt=cls.own_product,
            price=125,
            quantity=1,
        )
        cls.own_order = cls._create_order(
            cls.customer,
            first_name='Anna',
            status=Order.Status.PACKING,
            paid=True,
        )
        OrderItem.objects.create(
            order=cls.own_order,
            produkt=cls.own_product,
            price=250,
            quantity=2,
        )
        cls.other_order = cls._create_order(
            cls.other_customer,
            first_name='Hemlig kundinformation',
            status=Order.Status.PROCESSING,
            paid=True,
        )
        OrderItem.objects.create(
            order=cls.other_order,
            produkt=cls.other_product,
            price=333,
            quantity=1,
        )

    @classmethod
    def _create_order(cls, user, first_name, status, paid):
        return Order.objects.create(
            user=user,
            first_name=first_name,
            last_name='Kund',
            email=f'{user.username}@example.com',
            phone='0701234567',
            address='Testgatan 1',
            zipcode='12345',
            city='Stockholm',
            paid=paid,
            paid_amount=250,
            status=status,
        )

    def test_anonymous_user_is_redirected_from_order_list_and_detail(self):
        urls = (
            reverse('myaccount'),
            reverse('myaccount_order_detail', args=[self.own_order.pk]),
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f'{reverse("login")}?next={url}',
                    fetch_redirect_response=False,
                )

    def test_order_overview_contains_only_current_users_orders_newest_first(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse('myaccount'),
            {'user_id': self.other_customer.pk, 'username': self.other_customer.username},
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context['orders'],
            [self.own_order, self.older_order],
        )
        content = response.content.decode()
        self.assertLess(
            content.index(f'Order #{self.own_order.pk}'),
            content.index(f'Order #{self.older_order.pk}'),
        )
        self.assertNotContains(response, f'Order #{self.other_order.pk}')
        self.assertNotContains(response, 'Hemlig kundinformation')

    def test_customer_can_open_own_order_detail_with_correct_lines(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse('myaccount_order_detail', args=[self.own_order.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['order'], self.own_order)
        self.assertContains(response, self.own_product.namn)
        self.assertContains(response, 'Antal: 2')
        self.assertContains(response, '250,00 kr')
        self.assertNotContains(response, self.other_product.namn)
        self.assertNotContains(response, 'Hemlig kundinformation')

    def test_other_users_order_and_missing_order_return_not_found(self):
        self.client.force_login(self.customer)

        other_response = self.client.get(
            reverse('myaccount_order_detail', args=[self.other_order.pk]),
        )
        missing_response = self.client.get(
            reverse('myaccount_order_detail', args=[999999]),
        )

        self.assertEqual(other_response.status_code, 404)
        self.assertEqual(missing_response.status_code, 404)

    def test_staff_and_superuser_cannot_bypass_customer_ownership_filter(self):
        url = reverse('myaccount_order_detail', args=[self.own_order.pk])

        for user in (self.staff_user, self.superuser):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)

    def test_payment_and_operational_status_are_displayed(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse('myaccount_order_detail', args=[self.own_order.pk]),
        )

        self.assertContains(response, 'Betald')
        self.assertContains(response, 'Packas')

    def test_empty_order_history_renders_clear_empty_state(self):
        self.client.force_login(self.empty_customer)

        response = self.client.get(reverse('myaccount'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ingen orderhistorik ännu')

    def test_inactive_user_is_denied_from_order_pages(self):
        self.client.force_login(self.inactive_customer)

        for url in (
            reverse('myaccount'),
            reverse('myaccount_order_detail', args=[self.own_order.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f'{reverse("login")}?next={url}',
                    fetch_redirect_response=False,
                )

    def test_order_pages_are_private_and_not_cacheable(self):
        self.client.force_login(self.customer)

        for url in (
            reverse('myaccount'),
            reverse('myaccount_order_detail', args=[self.own_order.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                cache_control = response['Cache-Control']
                self.assertIn('private', cache_control)
                self.assertIn('no-cache', cache_control)
                self.assertIn('no-store', cache_control)

    def test_unpublished_product_still_renders_in_historical_order(self):
        self.own_product.publication_status = Produkt.PublicationStatus.ARCHIVED
        self.own_product.save(update_fields=['publication_status'])
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse('myaccount_order_detail', args=[self.own_order.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.own_product.namn)

    def test_product_used_by_order_item_is_protected_from_hard_delete(self):
        order_amount = self.own_order.paid_amount
        order_total = self.own_order.get_total_price()
        order_paid = self.own_order.paid
        inventory = self.own_product.inventory
        order_item_ids = list(
            OrderItem.objects.filter(produkt=self.own_product).values_list(
                'pk', flat=True
            )
        )

        with self.assertRaises(ProtectedError):
            self.own_product.delete()

        self.own_order.refresh_from_db()
        self.own_product.refresh_from_db()
        self.assertTrue(Order.objects.filter(pk=self.own_order.pk).exists())
        self.assertEqual(
            set(
                OrderItem.objects.filter(pk__in=order_item_ids).values_list(
                    'pk', flat=True
                )
            ),
            set(order_item_ids),
        )
        self.assertEqual(self.own_order.paid_amount, order_amount)
        self.assertEqual(self.own_order.get_total_price(), order_total)
        self.assertEqual(self.own_order.paid, order_paid)
        self.assertEqual(self.own_product.inventory, inventory)
