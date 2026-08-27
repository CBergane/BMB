from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.conf import settings
from django.template.defaultfilters import urlencode as template_urlencode
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

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


class ProductNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.parent_category = Category.objects.create(namn='Tyger')
        cls.category = Category.objects.create(
            namn='Bambujersey',
            parent=cls.parent_category,
        )
        cls.other_category = Category.objects.create(namn='Tillbehör')

        cls.newest = cls._create_product('Navigering nyast')
        cls.newer = cls._create_product('Navigering nyare')
        cls.current = cls._create_product('Bambujersey Beige')
        cls.older = cls._create_product('Navigering äldre')
        cls.oldest = cls._create_product('Navigering äldst')
        cls.tail = cls._create_product('Navigering sist')

        cls.draft = cls._create_product(
            'Dolt navigeringsutkast',
            publication_status=Produkt.PublicationStatus.DRAFT,
        )
        cls.archived = cls._create_product(
            'Dold arkiverad navigation',
            publication_status=Produkt.PublicationStatus.ARCHIVED,
        )
        cls.inactive = cls._create_product(
            'Dold inaktiv navigation',
            is_active=False,
        )
        cls.other_category_product = cls._create_product(
            'Annan kategoris produkt',
            category=cls.other_category,
        )

        base_time = timezone.now()
        ordered_products = (
            cls.newest,
            cls.newer,
            cls.current,
            cls.older,
            cls.oldest,
            cls.tail,
        )
        for position, product in enumerate(ordered_products):
            Produkt.objects.filter(pk=product.pk).update(
                skapad=base_time - timedelta(minutes=position),
            )

        hidden_times = (
            (cls.inactive, timedelta(seconds=30)),
            (cls.draft, timedelta(minutes=1, seconds=30)),
            (cls.archived, timedelta(minutes=2, seconds=30)),
        )
        for product, offset in hidden_times:
            Produkt.objects.filter(pk=product.pk).update(
                skapad=base_time - offset,
            )

    @classmethod
    def _create_product(
        cls,
        name,
        *,
        category=None,
        publication_status=Produkt.PublicationStatus.PUBLISHED,
        is_active=True,
    ):
        return Produkt.objects.create(
            category=category or cls.category,
            namn=name,
            inventory=10,
            is_active=is_active,
            pris=Decimal('149.00'),
            publication_status=publication_status,
        )

    def _detail_url(self, product=None):
        product = product or self.current
        return reverse('produkt', kwargs={'slug': product.slug})

    def _category_fallback(self):
        return (
            f"{reverse('shop')}?"
            f"{urlencode({'category': self.category.slug})}"
        )

    def test_breadcrumbs_show_parent_category_and_category(self):
        response = self.client.get(self._detail_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Brödsmulor"')
        self.assertContains(
            response,
            f'href="{reverse("shop")}?category={self.parent_category.slug}"',
        )
        self.assertContains(
            response,
            f'href="{reverse("shop")}?category={self.category.slug}"',
        )
        self.assertContains(response, 'aria-current="page">Bambujersey Beige')

    def test_product_card_carries_full_internal_list_context(self):
        list_query = {
            'category': self.category.slug,
            'query': 'Navigering',
            'page': '2',
        }
        response = self.client.get(reverse('shop'), list_query)
        list_context = (
            f"{reverse('shop')}?{urlencode(list_query)}"
            f"#product-{self.newer.pk}"
        )
        expected_href = (
            f"{self._detail_url(self.newer)}?return_to="
            f"{template_urlencode(list_context)}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="product-{self.newer.pk}"')
        self.assertContains(response, f'href="{expected_href}"')

    def test_internal_return_link_preserves_filters_page_and_anchor(self):
        return_to = (
            f"{reverse('shop')}?category={self.category.slug}"
            f"&query=beige&page=3#product-{self.current.pk}"
        )
        response = self.client.get(
            self._detail_url(),
            {'return_to': return_to},
        )

        self.assertEqual(response.context['return_to'], return_to)
        self.assertEqual(response.context['return_label'], self.category.namn)
        self.assertContains(response, f'href="{escape(return_to)}"')
        self.assertContains(response, 'Tillbaka till Bambujersey')

    def test_named_public_lists_are_allowed_return_contexts(self):
        list_contexts = (
            ('discounted_products', 'REA'),
            ('news', 'Nyheter'),
            ('stubbies', 'Stuvbitar'),
            ('bmb_exclusive_products', 'BMB Exclusive'),
        )

        for url_name, expected_label in list_contexts:
            return_to = (
                f"{reverse(url_name)}?page=2"
                f"#product-{self.current.pk}"
            )
            with self.subTest(url_name=url_name):
                response = self.client.get(
                    self._detail_url(),
                    {'return_to': return_to},
                )

                self.assertEqual(response.context['return_to'], return_to)
                self.assertEqual(
                    response.context['return_label'],
                    expected_label,
                )

    def test_external_and_unapproved_return_addresses_use_safe_fallback(self):
        fallback = self._category_fallback()
        unsafe_values = (
            'https://evil.example/phishing',
            '//evil.example/phishing',
            '/admin/?next=/shop/',
        )

        for return_to in unsafe_values:
            with self.subTest(return_to=return_to):
                response = self.client.get(
                    self._detail_url(),
                    {'return_to': return_to},
                )

                self.assertEqual(response.context['return_to'], fallback)
                self.assertNotContains(response, return_to)

    def test_direct_open_uses_category_fallback_or_shop(self):
        response = self.client.get(self._detail_url())

        self.assertEqual(response.context['return_to'], self._category_fallback())
        self.assertEqual(response.context['return_label'], self.category.namn)

        Category.objects.filter(pk=self.category.pk).update(slug='')
        response_without_category_slug = self.client.get(self._detail_url())

        self.assertEqual(
            response_without_category_slug.context['return_to'],
            reverse('shop'),
        )
        self.assertEqual(
            response_without_category_slug.context['return_label'],
            'Butik',
        )

    def test_previous_and_next_are_public_active_category_neighbors(self):
        response = self.client.get(self._detail_url())

        self.assertEqual(response.context['previous_product'], self.newer)
        self.assertEqual(response.context['next_product'], self.older)
        self.assertNotContains(response, self.draft.namn)
        self.assertNotContains(response, self.archived.namn)
        self.assertNotContains(response, self.inactive.namn)
        self.assertNotContains(response, self.other_category_product.namn)

    def test_previous_and_next_navigation_is_not_circular(self):
        first_response = self.client.get(self._detail_url(self.newest))
        last_response = self.client.get(self._detail_url(self.tail))

        self.assertIsNone(first_response.context['previous_product'])
        self.assertIsNone(last_response.context['next_product'])

    def test_related_products_exclude_current_hidden_and_other_categories(self):
        response = self.client.get(self._detail_url())
        related_products = list(response.context['related_products'])

        self.assertEqual(
            related_products,
            [self.newest, self.newer, self.older, self.oldest],
        )
        self.assertNotIn(self.current, related_products)
        self.assertNotIn(self.draft, related_products)
        self.assertNotIn(self.archived, related_products)
        self.assertNotIn(self.inactive, related_products)
        self.assertNotIn(self.other_category_product, related_products)
