from django.test import TestCase
from django.urls import reverse


class GotsVideoModalTests(TestCase):
    def test_frontpage_uses_playable_privacy_enhanced_gots_embed(self):
        response = self.client.get(reverse("frontpage"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertIn(
            'src="https://www.youtube-nocookie.com/embed/xhQiGhnbDqw"',
            html,
        )
        self.assertIn(
            'referrerpolicy="strict-origin-when-cross-origin"',
            html,
        )
        self.assertIn(
            'allow="accelerometer; autoplay; clipboard-write; '
            'encrypted-media; gyroscope; picture-in-picture; web-share"',
            html,
        )
        self.assertIn('aria-controls="myModal"', html)
        self.assertIn('aria-expanded="false"', html)
