from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Meddelande
from products.models import Category, Produkt


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

    def test_product_detail_renders(self):
        response = self.client.get(
            reverse("produkt", kwargs={"slug": self.product.slug}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.namn)
