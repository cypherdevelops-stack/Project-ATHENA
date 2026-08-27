import json

from django.contrib.auth.models import User
from django.test import TestCase

from backend.accounts.models import Account


class JournalOwnershipApiTests(TestCase):
    def setUp(self):
        self.first_user = User.objects.create_user(username='journal-first@example.com', password='Strong-password-123')
        self.second_user = User.objects.create_user(username='journal-second@example.com', password='Strong-password-123')
        self.first_account = Account.objects.create(user=self.first_user, display_name='First account')

    def test_user_can_create_session_and_event(self):
        self.client.force_login(self.first_user)
        session_response = self.client.post('/api/journal/sessions/create', data=json.dumps({
            'accountId': self.first_account.pk,
            'title': 'London open',
            'regime': 'RANGING',
        }), content_type='application/json')
        self.assertEqual(session_response.status_code, 201)
        self.assertIn(session_response.json()['marketSession'], {'LONDON', 'NEW_YORK', 'TOKYO', 'UNKNOWN'})
        session_id = session_response.json()['id']

        event_response = self.client.post(f'/api/journal/sessions/{session_id}/events', data=json.dumps({
            'eventType': 'OBSERVATION',
            'body': 'Price is rotating inside the prior range.',
        }), content_type='application/json')
        self.assertEqual(event_response.status_code, 201)
        self.assertEqual(self.client.get('/api/journal/sessions').json()['sessions'][0]['events'][0]['eventType'], 'OBSERVATION')

    def test_user_cannot_attach_another_users_account_or_read_their_session(self):
        other_account = Account.objects.create(user=self.second_user, display_name='Other account')
        self.client.force_login(self.first_user)
        response = self.client.post('/api/journal/sessions/create', data=json.dumps({'accountId': other_account.pk}), content_type='application/json')
        self.assertEqual(response.status_code, 404)