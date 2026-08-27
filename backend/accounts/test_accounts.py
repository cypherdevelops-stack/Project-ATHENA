import json

from django.contrib.auth.models import User
from django.test import TestCase
from unittest.mock import patch

from .models import Account, AccountInstrumentCapability


class AccountOwnershipApiTests(TestCase):
    def setUp(self):
        self.first_user = User.objects.create_user(username='first@example.com', password='Strong-password-123')
        self.second_user = User.objects.create_user(username='second@example.com', password='Strong-password-123')
        self.first_account = Account.objects.create(user=self.first_user, display_name='First account')
        self.second_account = Account.objects.create(user=self.second_user, display_name='Second account')
        AccountInstrumentCapability.objects.create(
            account=self.first_account,
            canonical_asset='XAUUSD',
            broker_symbol='XAUUSDc.Z',
            filling_modes=['IOC'],
        )

    def test_account_list_and_capabilities_are_scoped_to_authenticated_user(self):
        self.client.force_login(self.first_user)

        response = self.client.get('/api/account/list')

        self.assertEqual(response.status_code, 200)
        accounts = response.json()['accounts']
        self.assertEqual([account['displayName'] for account in accounts], ['First account'])
        self.assertEqual(accounts[0]['instrumentCapabilities'][0]['brokerSymbol'], 'XAUUSDc.Z')

    def test_user_cannot_update_delete_or_build_paper_trade_for_other_users_account(self):
        self.client.force_login(self.first_user)
        body = json.dumps({'accountId': self.second_account.pk, 'display_name': 'Hijacked'})

        update_response = self.client.patch('/api/account/update', data=body, content_type='application/json')
        delete_response = self.client.delete('/api/account/delete', data=json.dumps({'id': self.second_account.pk}), content_type='application/json')
        paper_response = self.client.post('/api/account/paper-trade', data=body, content_type='application/json')

        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(paper_response.status_code, 404)
        self.second_account.refresh_from_db()
        self.assertEqual(self.second_account.display_name, 'Second account')

    def test_user_can_select_only_their_own_default_account(self):
        self.client.force_login(self.first_user)
        response = self.client.post('/api/account/default', data=json.dumps({'accountId': self.first_account.pk}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['isDefault'])
        self.first_account.refresh_from_db()
        self.assertTrue(self.first_account.is_default)

        forbidden = self.client.post('/api/account/default', data=json.dumps({'accountId': self.second_account.pk}), content_type='application/json')
        self.assertEqual(forbidden.status_code, 404)


class AccountCredentialPersistenceTests(TestCase):
    def test_account_password_is_stored_encrypted_and_recovered_for_mt5_login(self):
        user = User.objects.create_user(username='credential@example.com', password='Strong-password-123')
        self.client.force_login(user)

        with patch('backend.accounts.views.encrypt_password', return_value='encrypted-broker-password'):
            response = self.client.post('/api/account/create', data=json.dumps({
                'accountNickname': 'MT5 account',
                'platform': 'MT5',
                'login': '123456',
                'password': 'raw-broker-password',
                'server': 'Demo-Server',
            }), content_type='application/json')

        self.assertEqual(response.status_code, 201)
        account = Account.objects.get(user=user)
        self.assertEqual(account.password_encrypted, 'encrypted-broker-password')
        self.assertNotEqual(account.password_encrypted, 'raw-broker-password')

        mt5 = type('FakeMt5', (), {
            'initialize': lambda self, **kwargs: True,
            'login': lambda self, **kwargs: kwargs['password'] == 'raw-broker-password',
            'account_info': lambda self: type('Info', (), {'trade_allowed': True, 'balance': 1000, 'trade_mode': 0})(),
            'shutdown': lambda self: None,
        })()
        with patch('backend.accounts.monitor._load_mt5', return_value=mt5), patch('backend.accounts.monitor.decrypt_password', return_value='raw-broker-password'):
            from backend.accounts.monitor import check_account
            account.enabled = True
            check_account(account)

        account.refresh_from_db()
        self.assertEqual(account.handshake_status, 'CONNECTED')

    def test_credentials_can_be_updated_without_returning_password(self):
        user = User.objects.create_user(username='update@example.com', password='Strong-password-123')
        account = Account.objects.create(user=user, display_name='Existing MT5 account')
        self.client.force_login(user)

        with patch('backend.accounts.views.encrypt_password', return_value='updated-encrypted-password'):
            response = self.client.patch('/api/account/update', data=json.dumps({
                'accountId': account.pk,
                'password': 'new-broker-password',
                'terminal_path': 'C:/MT5/terminal64.exe',
            }), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('password', response.json())
        account.refresh_from_db()
        self.assertEqual(account.password_encrypted, 'updated-encrypted-password')
        self.assertEqual(account.terminal_path, 'C:/MT5/terminal64.exe')

    def test_account_policy_updates_return_guardian_payload_with_decimal_values(self):
        user = User.objects.create_user(username='policy@example.com', password='Strong-password-123')
        account = Account.objects.create(user=user, display_name='Policy account')
        self.client.force_login(user)

        response = self.client.patch('/api/account/update', data=json.dumps({
            'accountId': account.pk,
            'max_daily_drawdown': '3',
            'athena_safety_drawdown': '2',
            'max_overall_drawdown': '8',
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['guardian']['state'], 'DISABLED')
