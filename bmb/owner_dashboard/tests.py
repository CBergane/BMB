from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from django.db.models.deletion import ProtectedError

from order.models import Order, OrderItem
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
            publication_status=Produkt.PublicationStatus.PUBLISHED,
            pris=Decimal('100.00'),
        )
        Produkt.objects.create(
            category=category,
            namn='Lågt lager',
            inventory=5,
            is_active=True,
            publication_status=Produkt.PublicationStatus.DRAFT,
            pris=Decimal('120.00'),
        )
        Produkt.objects.create(
            category=category,
            namn='Slut i lager',
            inventory=0,
            is_active=False,
            publication_status=Produkt.PublicationStatus.ARCHIVED,
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
            'published': 1,
            'draft': 1,
            'archived': 1,
        })
        self.assertEqual(response.context['order_totals'], {
            'total': 3,
            'unpaid': 2,
        })
        self.assertContains(response, 'Senaste ordrarna')
        self.assertContains(response, 'Senaste Kund')
        self.assertContains(response, '299,00 kr')


class OwnerProductManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username='produktagare',
            email='produktagare@example.com',
            password='hemligt123',
        )
        cls.regular_user = User.objects.create_user(
            username='produktkund',
            password='hemligt123',
        )
        cls.staff_user = User.objects.create_user(
            username='produktpersonal',
            password='hemligt123',
            is_staff=True,
        )
        cls.category = Category.objects.create(namn='Ägarprodukter')
        cls.other_category = Category.objects.create(namn='Annan kategori')
        cls.draft_product = Produkt.objects.create(
            category=cls.category,
            namn='Utkastprodukt',
            inventory=8,
            pris=Decimal('100.00'),
            publication_status=Produkt.PublicationStatus.DRAFT,
        )
        cls.published_product = Produkt.objects.create(
            category=cls.category,
            namn='Publicerad produkt',
            inventory=12,
            pris=Decimal('200.00'),
            publication_status=Produkt.PublicationStatus.PUBLISHED,
        )
        cls.other_product = Produkt.objects.create(
            category=cls.other_category,
            namn='Annan produkt',
            inventory=2,
            pris=Decimal('300.00'),
            publication_status=Produkt.PublicationStatus.ARCHIVED,
        )
        cls.combined_filter_product = Produkt.objects.create(
            category=cls.category,
            namn='Kombinerad Utkastprodukt',
            inventory=5,
            pris=Decimal('175.00'),
            publication_status=Produkt.PublicationStatus.DRAFT,
            is_active=True,
        )
        cls.order = Order.objects.create(
            user=cls.regular_user,
            first_name='Produkt',
            last_name='Kund',
            email='produktkund@example.com',
            phone='0700000000',
            address='Testgatan 1',
            zipcode='12345',
            city='Stockholm',
            paid=True,
            paid_amount=200,
        )
        OrderItem.objects.create(
            order=cls.order,
            produkt=cls.published_product,
            price=200,
            quantity=1,
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def _product_payload(self, product=None, **overrides):
        product = product or self.draft_product
        payload = {
            'namn': product.namn,
            'category': str(product.category_id),
            'beskrivning': 'Produktbeskrivning',
            'pris': str(product.pris),
            'inventory': str(product.inventory),
            'unit': product.unit,
            'discount_percentage': str(product.discount_percentage or 0),
            'is_active': 'on' if product.is_active else '',
            'is_fabric': 'on' if product.is_fabric else '',
            'is_stubbie': 'on' if product.is_stubbie else '',
            'is_bmb_exclusive': 'on' if product.is_bmb_exclusive else '',
            'bredd': product.bredd or '',
            'vikt': product.vikt or '',
            'length': product.length or '',
            'blandning': product.blandning or '',
            'kvalitet': product.kvalitet or '',
            'färg': product.färg or '',
            'motiv': product.motiv or '',
            'image_url': product.image_url or '',
            'variants-TOTAL_FORMS': '1',
            'variants-INITIAL_FORMS': '0',
            'variants-MIN_NUM_FORMS': '0',
            'variants-MAX_NUM_FORMS': '1000',
            'variants-0-additional_price': '0.00',
        }
        payload.update(overrides)
        return payload

    def test_product_views_require_active_superuser(self):
        urls = (
            reverse('owner_dashboard:product_list'),
            reverse('owner_dashboard:product_create'),
            reverse('owner_dashboard:product_edit', args=[self.draft_product.pk]),
            reverse('owner_dashboard:product_preview', args=[self.draft_product.pk]),
            reverse('owner_dashboard:product_publish', args=[self.draft_product.pk]),
            reverse('owner_dashboard:product_move_to_draft', args=[self.draft_product.pk]),
            reverse('owner_dashboard:product_archive', args=[self.draft_product.pk]),
        )
        for user in (self.regular_user, self.staff_user):
            self.client.force_login(user)
            for url in urls:
                with self.subTest(user=user.username, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_from_all_product_views(self):
        self.client.logout()
        urls = (
            reverse('owner_dashboard:product_list'),
            reverse('owner_dashboard:product_create'),
            reverse('owner_dashboard:product_edit', args=[self.draft_product.pk]),
            reverse('owner_dashboard:product_preview', args=[self.draft_product.pk]),
            reverse('owner_dashboard:product_publish', args=[self.draft_product.pk]),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f'{reverse("login")}?next={url}',
                    fetch_redirect_response=False,
                )

    def test_product_list_searches_and_filters(self):
        url = reverse('owner_dashboard:product_list')
        filter_cases = (
            ({'q': 'Utkast'}, (self.draft_product, self.combined_filter_product)),
            ({'status': 'draft'}, (self.draft_product, self.combined_filter_product)),
            ({'active': 'yes'}, (self.draft_product, self.published_product, self.combined_filter_product)),
            ({'category': self.category.pk}, (self.draft_product, self.published_product, self.combined_filter_product)),
            ({'low_stock': 'on'}, (self.other_product, self.combined_filter_product)),
        )

        for query, expected_products in filter_cases:
            with self.subTest(query=query):
                response = self.client.get(url, query)

                self.assertEqual(response.status_code, 200)
                for product in expected_products:
                    self.assertContains(response, product.namn)

        response = self.client.get(url, {'status': 'published'})
        self.assertContains(response, self.published_product.namn)
        self.assertNotContains(response, self.draft_product.namn)

    def test_product_list_combined_filters_use_and_logic(self):
        response = self.client.get(
            reverse('owner_dashboard:product_list'),
            {
                'q': 'Kombinerad',
                'status': 'draft',
                'active': 'yes',
                'category': self.category.pk,
                'low_stock': 'on',
            },
        )

        self.assertEqual(response.status_code, 200)
        result_products = list(response.context['page_obj'].object_list)
        result_ids = {product.pk for product in result_products}
        self.assertEqual(len(result_products), 1)
        self.assertIn(self.combined_filter_product.pk, result_ids)
        self.assertNotIn(self.draft_product.pk, result_ids)
        self.assertContains(response, self.combined_filter_product.namn)

    def test_create_always_saves_as_draft_even_when_status_is_manipulated(self):
        product_count = Produkt.objects.count()
        response = self.client.post(
            reverse('owner_dashboard:product_create'),
            self._product_payload(
                namn='Ny säker produkt',
                publication_status='published',
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Produkt.objects.count(), product_count + 1)
        product = Produkt.objects.get(namn='Ny säker produkt')
        self.assertEqual(product.publication_status, Produkt.PublicationStatus.DRAFT)
        self.assertEqual(product.category_id, self.category.pk)
        self.assertEqual(product.pris, Decimal('100.00'))
        self.assertEqual(product.inventory, 8)
        self.assertEqual(product.unit, 'st')

    def test_product_can_be_edited(self):
        response = self.client.post(
            reverse('owner_dashboard:product_edit', args=[self.draft_product.pk]),
            self._product_payload(namn='Uppdaterad produkt'),
        )

        self.assertEqual(response.status_code, 302)
        self.draft_product.refresh_from_db()
        self.assertEqual(self.draft_product.namn, 'Uppdaterad produkt')
        self.assertEqual(self.draft_product.publication_status, Produkt.PublicationStatus.DRAFT)
        self.assertEqual(self.draft_product.pris, Decimal('100.00'))
        self.assertEqual(self.draft_product.inventory, 8)

    def test_preview_shows_draft_but_has_no_cart_action(self):
        response = self.client.get(
            reverse('owner_dashboard:product_preview', args=[self.draft_product.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Förhandsgranskning')
        self.assertContains(response, 'inte publik')
        self.assertNotContains(response, reverse('add_to_cart', args=[self.draft_product.pk]))

    def test_public_product_url_still_hides_draft(self):
        response = self.client.get(
            reverse('produkt', kwargs={'slug': self.draft_product.slug}),
        )

        self.assertEqual(response.status_code, 404)

    def test_publication_actions_require_post_and_do_not_change_inventory_or_order_history(self):
        original_inventory = self.draft_product.inventory
        original_price = self.draft_product.pris
        original_order_count = Order.objects.count()

        for url_name, expected_status in (
            ('owner_dashboard:product_publish', Produkt.PublicationStatus.PUBLISHED),
            ('owner_dashboard:product_move_to_draft', Produkt.PublicationStatus.DRAFT),
            ('owner_dashboard:product_archive', Produkt.PublicationStatus.ARCHIVED),
        ):
            url = reverse(url_name, args=[self.draft_product.pk])
            get_response = self.client.get(url)
            self.assertEqual(get_response.status_code, 405)

            response = self.client.post(url)
            self.assertEqual(response.status_code, 302)
            self.draft_product.refresh_from_db()
            self.assertEqual(self.draft_product.publication_status, expected_status)

        self.draft_product.refresh_from_db()
        self.assertEqual(self.draft_product.inventory, original_inventory)
        self.assertEqual(self.draft_product.pris, original_price)
        self.assertEqual(Order.objects.count(), original_order_count)

    def test_publication_action_rejects_missing_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.superuser)

        response = csrf_client.post(
            reverse('owner_dashboard:product_publish', args=[self.draft_product.pk]),
        )

        self.assertEqual(response.status_code, 403)

    def test_product_with_order_history_cannot_be_hard_deleted(self):
        original_inventory = self.published_product.inventory
        original_price = self.published_product.pris

        with self.assertRaises(ProtectedError):
            self.published_product.delete()

        self.published_product.refresh_from_db()
        self.assertTrue(OrderItem.objects.filter(order=self.order, produkt=self.published_product).exists())
        self.assertEqual(self.published_product.inventory, original_inventory)
        self.assertEqual(self.published_product.pris, original_price)

    def test_regular_user_cannot_see_owner_form_or_preview_data(self):
        self.client.force_login(self.regular_user)

        for url in (
            reverse('owner_dashboard:product_edit', args=[self.draft_product.pk]),
            reverse('owner_dashboard:product_preview', args=[self.draft_product.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)
