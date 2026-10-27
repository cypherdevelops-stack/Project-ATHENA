import json

from django.contrib.auth.models import User
from django.test import TestCase


class AuthenticationApiTests(TestCase):
    def test_signup_hashes_password_and_creates_session(self):
        response = self.client.post(
            '/api/auth/signup',
            data=json.dumps({
                'email': 'trader@example.com',
                'password': 'Strong-password-123',
                'passwordConfirmation': 'Strong-password-123',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='trader@example.com')
        self.assertNotEqual(user.password, 'Strong-password-123')
        self.assertTrue(user.check_password('Strong-password-123'))
        self.assertIsNotNone(response.json()['user'])

    def test_login_rejects_wrong_password(self):
        User.objects.create_user(
            username='trader@example.com',
            email='trader@example.com',
            password='Strong-password-123',
        )

        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({'email': 'trader@example.com', 'password': 'wrong'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['detail'], 'Incorrect password.')

    def test_login_accepts_superuser_username_and_email(self):
        User.objects.create_superuser(
            username='athena-admin',
            email='admin@example.com',
            password='Strong-password-123',
        )

        for identifier in ('athena-admin', 'admin@example.com'):
            response = self.client.post(
                '/api/auth/login',
                data=json.dumps({'email': identifier, 'password': 'Strong-password-123'}),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.client.logout()

    def test_signup_rejects_an_email_that_differs_only_by_case(self):
        User.objects.create_user(
            username='trader@example.com',
            email='trader@example.com',
            password='Strong-password-123',
        )

        response = self.client.post(
            '/api/auth/signup',
            data=json.dumps({
                'email': 'TRADER@example.com',
                'password': 'Another-strong-password-123',
                'passwordConfirmation': 'Another-strong-password-123',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(User.objects.filter(email__iexact='trader@example.com').count(), 1)

    def test_session_requires_no_password_and_reports_authenticated_user(self):
        user = User.objects.create_user(
            username='trader@example.com',
            email='trader@example.com',
            password='Strong-password-123',
        )
        self.client.force_login(user)

        response = self.client.get('/api/auth/session')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['email'], 'trader@example.com')
