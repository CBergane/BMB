from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from products.models import Category, Produkt


class ProductPublicationLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.parent_category = Category.objects.create(namn='Livscykel')
        cls.category = Category.objects.create(
            namn='Publicering',
            parent=cls.parent_category,
        )
        common = {
            'category': cls.category,
            'inventory': 10,
            'is_active': True,
            'pris': Decimal('98.34'),
            'discount_percentage': 10,
            'is_bmb_exclusive': True,
        }
        cls.published_product = Produkt.objects.create(
            namn='Publicerad produkt',
            publication_status=Produkt.PublicationStatus.PUBLISHED,
            **common,
        )
        cls.draft_product = Produkt.objects.create(
            namn='Produktutkast',
            publication_status=Produkt.PublicationStatus.DRAFT,
            **common,
        )
        cls.archived_product = Produkt.objects.create(
            namn='Arkiverad produkt',
            publication_status=Produkt.PublicationStatus.ARCHIVED,
            **common,
        )
        cls.inactive_product = Produkt.objects.create(
            namn='Inaktiv publicerad produkt',
            publication_status=Produkt.PublicationStatus.PUBLISHED,
            is_active=False,
            **{key: value for key, value in common.items() if key != 'is_active'},
        )
        cls.published_stubbie = Produkt.objects.create(
            namn='Publicerad stuvbit',
            publication_status=Produkt.PublicationStatus.PUBLISHED,
            category=cls.category,
            inventory=1,
            is_active=True,
            pris=Decimal('75.00'),
            is_stubbie=True,
            length=Decimal('4.00'),
        )

    def test_new_product_defaults_to_draft(self):
        product = Produkt.objects.create(
            category=self.category,
            namn='Nytt utkast',
            inventory=1,
            is_active=True,
            pris=Decimal('50.00'),
        )

        self.assertEqual(product.publication_status, Produkt.PublicationStatus.DRAFT)

    def test_public_queryset_only_contains_published_active_products(self):
        self.assertQuerySetEqual(
            Produkt.objects.public().order_by('pk'),
            [self.published_product, self.published_stubbie],
        )

    def test_public_lists_hide_draft_archived_and_inactive_products(self):
        list_requests = (
            (reverse('frontpage'), {}),
            (reverse('news'), {}),
            (reverse('shop'), {'category': self.category.slug}),
            (reverse('discounted_products'), {}),
            (reverse('bmb_exclusive_products'), {}),
        )

        for url, query in list_requests:
            with self.subTest(url=url):
                response = self.client.get(url, query)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, self.published_product.namn)
                self.assertNotContains(response, self.draft_product.namn)
                self.assertNotContains(response, self.archived_product.namn)
                self.assertNotContains(response, self.inactive_product.namn)

        stubbie_response = self.client.get(reverse('stubbies'))
        self.assertEqual(stubbie_response.status_code, 200)
        self.assertContains(stubbie_response, self.published_stubbie.namn)
        self.assertNotContains(stubbie_response, self.draft_product.namn)
        self.assertNotContains(stubbie_response, self.archived_product.namn)
        self.assertNotContains(stubbie_response, self.inactive_product.namn)

    def test_unavailable_product_detail_urls_return_not_found(self):
        for product in (self.draft_product, self.archived_product, self.inactive_product):
            with self.subTest(product=product.namn):
                response = self.client.get(
                    reverse('produkt', kwargs={'slug': product.slug}),
                )
                self.assertEqual(response.status_code, 404)

        published_response = self.client.get(
            reverse('produkt', kwargs={'slug': self.published_product.slug}),
        )
        self.assertEqual(published_response.status_code, 200)

    def test_unavailable_products_cannot_be_added_to_cart(self):
        for product in (self.draft_product, self.archived_product, self.inactive_product):
            with self.subTest(product=product.namn):
                response = self.client.post(
                    reverse('add_to_cart', args=[product.pk]),
                    {'quantity': 1},
                )
                self.assertEqual(response.status_code, 404)

    def test_saved_cart_reports_product_that_is_no_longer_public(self):
        session = self.client.session
        session[settings.CART_SESSION_ID] = {
            f'{self.draft_product.pk}_None_': {
                'produkt_id': self.draft_product.pk,
                'color_id': None,
                'custom_text': '',
                'quantity': 1,
            },
        }
        session.save()

        response = self.client.get(reverse('cart'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'inte längre publicerade eller tillgängliga')
        self.assertNotContains(response, self.draft_product.namn)
