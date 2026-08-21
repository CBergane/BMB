from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Meddelande
from core.templatetags.price_filters import sek
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
