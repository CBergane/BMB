import os
from unittest.mock import patch

from django.test import SimpleTestCase

from bmb import settings as project_settings


class EnvironmentSettingsParserTests(SimpleTestCase):
    def test_boolean_parser_defaults_to_false(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(project_settings._env_bool("UNSET_TEST_SETTING"))

    def test_boolean_parser_accepts_supported_true_values(self):
        for value in ("True", "true", "1", "yes", " YES "):
            with self.subTest(value=value), patch.dict(
                os.environ,
                {"TEST_BOOLEAN_SETTING": value},
            ):
                self.assertTrue(
                    project_settings._env_bool("TEST_BOOLEAN_SETTING")
                )

    def test_csv_parser_trims_values_and_ignores_empty_entries(self):
        with patch.dict(
            os.environ,
            {
                "TEST_CSV_SETTING": (
                    " https://example.com,https://www.example.com, ,"
                )
            },
        ):
            self.assertEqual(
                project_settings._env_csv("TEST_CSV_SETTING"),
                ["https://example.com", "https://www.example.com"],
            )
