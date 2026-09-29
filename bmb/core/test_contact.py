import re

from django.conf import settings
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='smtp-account@example.com',
    DEFAULT_FROM_EMAIL='Bra Mycket Bättre <site@example.com>',
)
class ContactFormTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.url = reverse('send_email')
        self.data = {
            'name': 'Anna Andersson',
            'email': 'anna@example.com',
            'message': 'Hej! Finns tyget kvar?',
        }

    def load_contact_token(self):
        response = self.client.get(reverse('frontpage'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        form = re.search(
            r'<form id="contactForm".*?</form>', response.content.decode(), re.S,
        ).group()
        token = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"', form,
        )
        self.assertIsNotNone(token, 'The contact form must render a CSRF token.')
        return token.group(1)

    def submit(self, token, data=None):
        return self.client.post(
            self.url, self.data if data is None else data,
            HTTP_X_CSRFTOKEN=token,
        )

    def test_first_time_anonymous_visitor_can_submit(self):
        self.assertNotIn(settings.CSRF_COOKIE_NAME, self.client.cookies)
        token = self.load_contact_token()
        self.assertIn(settings.CSRF_COOKIE_NAME, self.client.cookies)

        response = self.submit(token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'status': 'success', 'message': 'E-post skickad',
        })
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(len(mail.outbox), 1)

    def test_csrf_token_works_without_javascript_cookie_access(self):
        for options in ({'CSRF_COOKIE_HTTPONLY': True}, {'CSRF_USE_SESSIONS': True}):
            with self.subTest(options=options), override_settings(**options):
                self.client = Client(enforce_csrf_checks=True)
                token = self.load_contact_token()

                response = self.submit(token)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(len(mail.outbox), 2)

    def test_missing_or_invalid_csrf_is_rejected(self):
        token = self.load_contact_token()
        responses = (
            self.client.post(self.url, self.data),
            self.submit('invalid-token'),
            Client(enforce_csrf_checks=True).post(
                self.url, self.data, HTTP_X_CSRFTOKEN=token,
            ),
        )
        for response in responses:
            self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_is_rejected(self):
        token = self.load_contact_token()
        for email in ('invalid', 'anna@example.com\r\nBcc: injected@example.com'):
            with self.subTest(email=email):
                response = self.submit(token, {**self.data, 'email': email})

                self.assertEqual(response.json(), {
                    'status': 'error', 'message': 'Ogiltig e-postadress.',
                })
        self.assertEqual(len(mail.outbox), 0)

    def test_required_fields_reject_missing_empty_and_whitespace_values(self):
        token = self.load_contact_token()
        for field in self.data:
            for value in (None, '', ' \t\n '):
                with self.subTest(field=field, value=value):
                    data = {**self.data, field: value}
                    if value is None:
                        del data[field]

                    response = self.submit(token, data)

                    self.assertEqual(response.json(), {
                        'status': 'error', 'message': 'Alla fält måste fyllas i.',
                    })
        self.assertEqual(len(mail.outbox), 0)

    def test_unsupported_methods_are_not_allowed(self):
        token = self.load_contact_token()
        for method in ('GET', 'HEAD', 'OPTIONS', 'PUT', 'PATCH', 'DELETE', 'TRACE'):
            with self.subTest(method=method):
                response = self.client.generic(method, self.url, HTTP_X_CSRFTOKEN=token)

                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.headers['Allow'], 'POST')
        self.assertEqual(len(mail.outbox), 0)

    def test_email_uses_site_sender_and_visitor_reply_to(self):
        response = self.submit(self.load_contact_token())

        self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(email.reply_to, ['anna@example.com'])
        self.assertEqual(email.to, ['bmb@bramycketbattre.com'])
        self.assertEqual(email.subject, 'Meddelande från Anna Andersson via Kontaktformulär')
        self.assertEqual(email.body,
            'Namn: Anna Andersson\nE-post: anna@example.com\n\nMeddelande:\nHej! Finns tyget kvar?',
        )

    def test_name_punctuation_and_message_content_are_accepted_as_plain_text(self):
        data = {
            **self.data,
            'name': "  Anna-Lisa O'Neill  ",
            'email': '  anna@example.com  ',
            'message': '<script>alert("text")</script>\nMått: 2 < 3 > 1',
        }

        response = self.submit(self.load_contact_token(), data)

        self.assertEqual(response.json()['status'], 'success')
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Meddelande från Anna-Lisa O'Neill via Kontaktformulär")
        self.assertEqual(email.reply_to, ['anna@example.com'])
        self.assertIn(data['message'], email.body)
        self.assertEqual(email.message().get_content_type(), 'text/plain')

    def test_name_cannot_inject_email_headers(self):
        response = self.submit(self.load_contact_token(), {
            **self.data, 'name': 'Anna\r\nBcc: injected@example.com',
        })

        self.assertEqual(response.json(), {'status': 'error', 'message': 'Ogiltigt namn.'})
        self.assertEqual(len(mail.outbox), 0)
