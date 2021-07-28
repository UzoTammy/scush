from django.test import SimpleTestCase


class ApplyTests(SimpleTestCase):
    def test_apply_page_status_code(self):
        response = self.client.get('apply/')
        self.assertEqual(response.status_code, 200)
