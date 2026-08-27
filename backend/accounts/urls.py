from django.urls import path

from . import views

urlpatterns = [
    path('', views.account_view, name='account'),
    path('list', views.accounts_view, name='accounts'),
    path('mt5/health', views.mt5_health_view, name='mt5-health'),
    path('default', views.set_default_account_view, name='account-default'),
    path('create', views.create_account_view, name='account-create'),
    path('onboarding/discover', views.discover_account_view, name='account-discover'),
    path('settings/account/test-handshake', views.test_handshake_view, name='account-test-handshake'),
    path('update', views.update_account_view, name='account-update'),
    path('delete', views.delete_account_view, name='account-delete'),
    path('guardian', views.guardian_view, name='guardian'),
    path('paper-trade', views.paper_trade_view, name='paper-trade'),
]
