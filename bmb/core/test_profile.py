from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse


User = get_user_model()


class ProfileEditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='kund', password='original-password',
            first_name='Anna', last_name='Andersson', email='anna@example.com',
        )
        cls.other_user = User.objects.create_user(
            username='annan-kund', email='annan@example.com',
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('edit_myaccount')
        self.data = {
            'first_name': 'Lisa',
            'last_name': 'Svensson',
            'username': 'ny-kund',
            'email': 'lisa@example.com',
        }

    def test_get_prefills_only_editable_fields(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_bound)
        self.assertEqual(list(form.fields), ['first_name', 'last_name', 'username', 'email'])
        for field in form.fields:
            self.assertEqual(form[field].value(), getattr(self.user, field))
        self.assertContains(response, 'value="Anna"')
        self.assertContains(response, 'w-full mt-2 py-4 px-4 bg-gray-100 rounded-xl', count=4)

    def test_successful_edit_redirects_and_preserves_login(self):
        response = self.client.post(self.url, self.data)

        self.assertRedirects(response, reverse('myaccount'))
        self.user.refresh_from_db()
        for field, value in self.data.items():
            self.assertEqual(getattr(self.user, field), value)
        self.assertTrue(self.user.check_password('original-password'))
        page = self.client.get(reverse('myaccount'))
        self.assertEqual(page.wsgi_request.user.pk, self.user.pk)
        self.assertTrue(page.wsgi_request.user.is_authenticated)

    def test_anonymous_get_and_post_require_login(self):
        self.client.logout()
        for method in ('get', 'post'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.url, self.data)

                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(f'{reverse("login")}?next='))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'kund')

    def test_duplicate_username_shows_swedish_error(self):
        response = self.client.post(self.url, {
            **self.data, 'username': self.other_user.username,
        })

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'username', 'Användarnamnet är redan upptaget.')
        self.assertContains(response, 'Användarnamnet är redan upptaget.')
        self.other_user.refresh_from_db()
        self.assertEqual(self.other_user.email, 'annan@example.com')

    def test_current_username_remains_valid(self):
        response = self.client.post(self.url, {**self.data, 'username': self.user.username})

        self.assertRedirects(response, reverse('myaccount'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'kund')
        self.assertEqual(self.user.email, 'lisa@example.com')

    def test_username_rules_and_length_are_validated(self):
        for username in ('', 'invalid name', 'invalid/name', 'x' * 151):
            with self.subTest(username=username):
                response = self.client.post(self.url, {**self.data, 'username': username})

                self.assertEqual(response.status_code, 200)
                self.assertIn('username', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'kund')

    def test_username_uses_django_unicode_normalization(self):
        response = self.client.post(self.url, {**self.data, 'username': 'ｋｕｎｄ'})

        self.assertRedirects(response, reverse('myaccount'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'kund')

    def test_invalid_email_redisplays_submitted_values_and_error(self):
        response = self.client.post(self.url, {**self.data, 'email': 'invalid-email'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/edit_myaccount.html')
        self.assertFormError(response.context['form'], 'email', 'Ange en giltig e-postadress.')
        self.assertContains(response, 'Ange en giltig e-postadress.')
        self.assertContains(response, 'value="invalid-email"')
        self.assertContains(response, 'value="Lisa"')
        self.assertContains(response, 'value="ny-kund"')

    def test_invalid_submission_does_not_persist_any_changes(self):
        original = User.objects.values().get(pk=self.user.pk)

        response = self.client.post(self.url, {**self.data, 'email': 'invalid-email'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.values().get(pk=self.user.pk), original)

    def test_extra_fields_cannot_change_privileges_password_or_target_user(self):
        group = Group.objects.create(name='Privileged group')
        permission = Permission.objects.get(
            content_type__app_label='auth', codename='change_user',
        )
        other_original = User.objects.values().get(pk=self.other_user.pk)
        password = self.user.password

        response = self.client.post(self.url, {
            **self.data,
            'id': self.other_user.pk,
            'pk': self.other_user.pk,
            'user_id': self.other_user.pk,
            'is_staff': 'True',
            'is_superuser': 'True',
            'is_active': 'False',
            'password': 'injected-password',
            'groups': [group.pk],
            'user_permissions': [permission.pk],
        })

        self.assertRedirects(response, reverse('myaccount'))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.password, password)
        self.assertFalse(self.user.groups.exists())
        self.assertFalse(self.user.user_permissions.exists())
        self.assertEqual(User.objects.values().get(pk=self.other_user.pk), other_original)

    def test_names_accept_unicode_punctuation_and_trim_whitespace(self):
        response = self.client.post(self.url, {
            **self.data, 'first_name': '  Åsa-Lisa  ', 'last_name': "  O'Neill  ",
        })

        self.assertRedirects(response, reverse('myaccount'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Åsa-Lisa')
        self.assertEqual(self.user.last_name, "O'Neill")

    def test_names_respect_model_length_limits(self):
        for field in ('first_name', 'last_name'):
            with self.subTest(field=field):
                response = self.client.post(self.url, {**self.data, field: 'x' * 151})

                self.assertEqual(response.status_code, 200)
                self.assertFormError(response.context['form'], field, 'Ange högst 150 tecken.')
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Anna')
        self.assertEqual(self.user.last_name, 'Andersson')

    def test_names_and_email_remain_optional(self):
        response = self.client.post(self.url, {
            **self.data, 'first_name': '  ', 'last_name': '', 'email': '',
        })

        self.assertRedirects(response, reverse('myaccount'))
        self.user.refresh_from_db()
        for field in ('first_name', 'last_name', 'email'):
            self.assertEqual(getattr(self.user, field), '')

    def test_email_remains_non_unique_like_the_user_model(self):
        response = self.client.post(self.url, {**self.data, 'email': self.other_user.email})

        self.assertRedirects(response, reverse('myaccount'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, self.other_user.email)

    def test_csrf_protection_is_preserved(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)

        response = client.post(self.url, self.data)

        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'kund')

        page = client.get(self.url)
        response = client.post(self.url, {
            **self.data, 'csrfmiddlewaretoken': str(page.context['csrf_token']),
        })
        self.assertRedirects(response, reverse('myaccount'))
