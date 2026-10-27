from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from backend import frontend


class FrontendServingTests(SimpleTestCase):
    def test_root_and_client_routes_serve_the_frontend_build(self):
        with TemporaryDirectory() as directory:
            index = Path(directory) / 'index.html'
            index.write_text('<html><div id="root"></div></html>', encoding='utf-8')
            with patch.object(frontend, 'FRONTEND_INDEX', index):
                for url in ('/', '/settings', '/orchestration'):
                    with self.subTest(url=url):
                        response = self.client.get(url)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
                        self.assertContains(response, '<div id="root"></div>')

    def test_missing_frontend_build_returns_clear_404(self):
        with patch.object(frontend, 'FRONTEND_INDEX', Path('missing-frontend-index.html')):
            response = self.client.get('/')

        self.assertEqual(response.status_code, 404)
