from django.urls import path

from .views import datasets_view, drawings_view, market_data_view, replay_view

urlpatterns = [
    path('market-data', market_data_view, name='backtesting-market-data'),
    path('drawings', drawings_view, name='backtesting-drawings'),
    path('replay', replay_view, name='backtesting-replay'),
    path('datasets', datasets_view, name='backtesting-datasets'),
]
