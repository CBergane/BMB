from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.crypto import get_random_string

from django.db.models.deletion import ProtectedError

from order.models import (
    Order,
    OrderInventoryError,
    OrderItem,
    OrderStatusHistory,
    OrderStatusTransitionError,
)
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


class OwnerOrderManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = get_random_string(32)
        cls.superuser = User.objects.create(
            username='order-owner',
            email='order-owner@example.com',
            password=make_password(cls.password),
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        cls.customer = User.objects.create_user(
            username='order-customer',
            email='order-customer@example.com',
            password=get_random_string(32),
        )
        cls.other_customer = User.objects.create_user(
            username='other-order-customer',
            email='other-order-customer@example.com',
            password=get_random_string(32),
        )
        cls.staff_user = User.objects.create_user(
            username='order-staff',
            password=get_random_string(32),
            is_staff=True,
        )
        cls.category = Category.objects.create(namn='Orderkategori')
        cls.product = Produkt.objects.create(
            category=cls.category,
            namn='Orderprodukt',
            inventory=10,
            pris=Decimal('100.00'),
            is_active=True,
            publication_status=Produkt.PublicationStatus.PUBLISHED,
        )
        cls.short_product = Produkt.objects.create(
            category=cls.category,
            namn='Lagerbegränsad orderprodukt',
            inventory=1,
            pris=Decimal('125.00'),
            is_active=True,
            publication_status=Produkt.PublicationStatus.PUBLISHED,
        )
        cls.unpaid_order = cls._create_order(
            cls.customer,
            first_name='Obetald',
            email='unpaid@example.com',
        )
        OrderItem.objects.create(
            order=cls.unpaid_order,
            produkt=cls.product,
            price=100,
            quantity=2,
        )
        cls.detail_order = cls._create_order(
            cls.customer,
            first_name='Detalj',
            email='detail@example.com',
            status=Order.Status.PACKING,
            paid=True,
        )
        OrderItem.objects.create(
            order=cls.detail_order,
            produkt=cls.product,
            price=100,
            quantity=1,
        )
        cls.other_order = cls._create_order(
            cls.other_customer,
            first_name='Annan kund',
            email='other@example.com',
        )
        cls.list_orders = []
        for label in 'abcdefghijklmnopqrstu':
            cls.list_orders.append(cls._create_order(
                cls.customer,
                first_name=f'Lista {label}',
                email=f'list-{label}@example.com',
            ))

    @classmethod
    def _create_order(cls, user, first_name, email, status=Order.Status.RECEIVED, paid=False):
        return Order.objects.create(
            user=user,
            first_name=first_name,
            last_name='Testkund',
            email=email,
            phone='0700000000',
            address='Ordergatan 1',
            zipcode='12345',
            city='Stockholm',
            status=status,
            paid=paid,
            paid_amount=100,
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_owner_order_views_require_active_superuser(self):
        urls = (
            reverse('owner_dashboard:order_list'),
            reverse('owner_dashboard:order_detail', args=[self.unpaid_order.pk]),
            reverse('owner_dashboard:order_mark_paid', args=[self.unpaid_order.pk]),
            reverse('owner_dashboard:order_change_status', args=[self.unpaid_order.pk, 'archived']),
        )
        anonymous_client = Client()
        for url in urls:
            with self.subTest(url=url):
                response = anonymous_client.get(url)
                self.assertEqual(response.status_code, 302)

        for user in (self.customer, self.staff_user):
            self.client.force_login(user)
            for url in urls:
                with self.subTest(user=user.username, url=url):
                    self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(reverse('owner_dashboard:order_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('owner_dashboard:order_detail', args=[self.unpaid_order.pk])).status_code, 200)

    def _result_ids(self, response):
        return {order.pk for order in list(response.context['page_obj'].object_list)}

    def test_order_list_searches_by_unique_order_number(self):
        url = reverse('owner_dashboard:order_list')

        response = self.client.get(url, {'q': str(self.unpaid_order.pk)})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertEqual(self._result_ids(response), {self.unpaid_order.pk})

    def test_order_list_searches_customer_name_and_email(self):
        url = reverse('owner_dashboard:order_list')

        for query, expected_order in (
            (self.list_orders[0].first_name, self.list_orders[0]),
            (self.list_orders[1].email, self.list_orders[1]),
        ):
            with self.subTest(query=query):
                response = self.client.get(url, {'q': query})
                result_orders = list(response.context['page_obj'].object_list)

                self.assertEqual(response.context['page_obj'].paginator.count, 1)
                self.assertEqual(len(result_orders), 1)
                self.assertEqual({order.pk for order in result_orders}, {expected_order.pk})
                self.assertEqual(result_orders[0].user_id, self.customer.pk)

    def test_order_list_filters_paid_and_operational_status(self):
        url = reverse('owner_dashboard:order_list')

        response = self.client.get(url, {'q': 'Obetald', 'paid': 'no', 'status': 'received'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertEqual(self._result_ids(response), {self.unpaid_order.pk})

        response = self.client.get(url, {'paid': 'yes'})
        self.assertEqual(self._result_ids(response), {self.detail_order.pk})

        response = self.client.get(url, {'status': 'packing'})
        self.assertEqual(self._result_ids(response), {self.detail_order.pk})

    def test_order_list_paginates(self):
        url = reverse('owner_dashboard:order_list')

        response = self.client.get(url, {'page': 2})
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertGreater(response.context['page_obj'].paginator.num_pages, 1)

    def test_order_list_combined_filters_use_and_logic(self):
        response = self.client.get(
            reverse('owner_dashboard:order_list'),
            {'q': 'Obetald', 'paid': 'no', 'status': 'received'},
        )

        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertEqual(self._result_ids(response), {self.unpaid_order.pk})

    def test_order_detail_shows_customer_and_historical_order_lines_without_delete_action(self):
        response = self.client.get(
            reverse('owner_dashboard:order_detail', args=[self.detail_order.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.detail_order.email)
        self.assertContains(response, self.product.namn)
        self.assertContains(response, 'Antal: 1')
        self.assertContains(response, 'Packas')
        self.assertContains(response, 'Betald')
        self.assertNotContains(response, 'Radera')

    def test_mark_paid_is_post_only_csrf_protected_and_idempotent(self):
        url = reverse('owner_dashboard:order_mark_paid', args=[self.unpaid_order.pk])
        self.assertEqual(self.client.get(url).status_code, 405)

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.superuser)
        self.assertEqual(csrf_client.post(url).status_code, 403)

        initial_inventory = self.product.inventory
        first_response = self.client.post(url)
        self.assertEqual(first_response.status_code, 302)
        self.product.refresh_from_db()
        self.unpaid_order.refresh_from_db()
        self.assertTrue(self.unpaid_order.paid)
        self.assertEqual(self.product.inventory, initial_inventory - 2)

        second_response = self.client.post(url)
        self.assertEqual(second_response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, initial_inventory - 2)

    def test_mark_paid_rolls_back_when_inventory_is_insufficient(self):
        order = self._create_order(self.customer, 'För lite lager', 'short@example.com')
        OrderItem.objects.create(order=order, produkt=self.short_product, price=125, quantity=2)
        url = reverse('owner_dashboard:order_mark_paid', args=[order.pk])

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.short_product.refresh_from_db()
        self.assertFalse(order.paid)
        self.assertEqual(self.short_product.inventory, 1)
        self.assertEqual(OrderItem.objects.filter(order=order).count(), 1)

    def test_allowed_status_transitions_create_one_history_row(self):
        order = self._create_order(self.customer, 'Statuskedja', 'status-chain@example.com', paid=True)
        for status in (
            Order.Status.PROCESSING,
            Order.Status.PACKING,
            Order.Status.SHIPPED,
            Order.Status.COMPLETED,
            Order.Status.ARCHIVED,
        ):
            order.transition_status(status, changed_by=self.superuser)

        self.assertEqual(
            OrderStatusHistory.objects.filter(order=order).count(),
            5,
        )
        self.assertEqual(order.status, Order.Status.ARCHIVED)
        self.assertEqual(
            OrderStatusHistory.objects.filter(order=order).first().new_status,
            Order.Status.ARCHIVED,
        )

    def test_unpaid_received_order_can_be_cancelled_or_archived(self):
        cancelled = self._create_order(self.customer, 'Avbryt', 'cancel@example.com')
        archived = self._create_order(self.customer, 'Arkivera', 'archive@example.com')

        cancelled.transition_status(Order.Status.CANCELLED, changed_by=self.superuser)
        archived.transition_status(Order.Status.ARCHIVED, changed_by=self.superuser)

        self.assertEqual(cancelled.status, Order.Status.CANCELLED)
        self.assertEqual(archived.status, Order.Status.ARCHIVED)
        self.assertEqual(OrderStatusHistory.objects.filter(order=cancelled).count(), 1)
        self.assertEqual(OrderStatusHistory.objects.filter(order=archived).count(), 1)

    def test_forbidden_status_transitions_do_not_change_order_or_history(self):
        cases = (
            (Order.Status.RECEIVED, False, Order.Status.PROCESSING),
            (Order.Status.RECEIVED, True, Order.Status.CANCELLED),
            (Order.Status.PROCESSING, False, Order.Status.PACKING),
            (Order.Status.SHIPPED, True, Order.Status.ARCHIVED),
            (Order.Status.ARCHIVED, True, Order.Status.COMPLETED),
        )
        for status, paid, target in cases:
            with self.subTest(status=status, paid=paid, target=target):
                order = self._create_order(
                    self.customer,
                    'Otillåten',
                    f'forbidden-{status}-{target}@example.com',
                    status=status,
                    paid=paid,
                )
                with self.assertRaises(OrderStatusTransitionError):
                    order.transition_status(target, changed_by=self.superuser)
                order.refresh_from_db()
                self.assertEqual(order.status, status)
                self.assertEqual(OrderStatusHistory.objects.filter(order=order).count(), 0)

    def test_status_action_creates_history_with_owner_and_customer_sees_update(self):
        order = self._create_order(self.customer, 'Kundstatus', 'customer-status@example.com', paid=True)
        url = reverse('owner_dashboard:order_change_status', args=[order.pk, 'processing'])

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        history = OrderStatusHistory.objects.get(order=order)
        self.assertEqual(history.changed_by, self.superuser)
        self.client.force_login(self.customer)
        customer_response = self.client.get(reverse('myaccount_order_detail', args=[order.pk]))
        self.assertContains(customer_response, 'Behandlas')

    def test_status_action_rejects_invalid_transition_without_history(self):
        url = reverse('owner_dashboard:order_change_status', args=[self.unpaid_order.pk, 'processing'])

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(OrderStatusHistory.objects.filter(order=self.unpaid_order).count(), 0)
        self.unpaid_order.refresh_from_db()
        self.assertEqual(self.unpaid_order.status, Order.Status.RECEIVED)

    def test_other_customer_cannot_view_order_detail(self):
        self.client.force_login(self.other_customer)

        response = self.client.get(
            reverse('myaccount_order_detail', args=[self.detail_order.pk]),
        )

        self.assertEqual(response.status_code, 404)
