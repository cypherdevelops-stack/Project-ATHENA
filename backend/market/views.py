from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from backend.accounts.models import Account

from .context import classify_regime
from .service import MarketDataError, market_data_service


@login_required
@require_GET
def context_view(request):
    account = Account.objects.filter(user=request.user, pk=request.GET.get('accountId')).first()
    if account is None:
        account = Account.objects.filter(user=request.user, is_default=True, enabled=True).first() or Account.objects.filter(user=request.user, enabled=True).first()
    if account is None:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': 'No trading account is available.'})
    if not account.broker_symbol:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': 'No broker symbol has been discovered.'})

    timeframe = request.GET.get('timeframe', 'M15').upper()
    try:
        data = market_data_service.fetch(account, timeframes=(timeframe,), candle_count=100)
        candles = data.candles[timeframe]
        snapshot = data.snapshot.as_dict()
        return JsonResponse({
            'symbol': snapshot['brokerSymbol'],
            'bid': snapshot['bid'],
            'ask': snapshot['ask'],
            'spread': snapshot['spread'],
            'timestamp': snapshot['timestamp'],
            'mt5Time': snapshot['mt5Time'],
            'receivedAt': snapshot['receivedAt'],
            'latencyMs': snapshot['latencyMs'],
            'timeframe': timeframe,
            'candleCount': len(candles),
            'latestCandle': candles[-1] if candles else None,
            'regime': classify_regime(candles),
            'status': 'HEALTHY' if candles else 'UNAVAILABLE',
        })
    except MarketDataError as error:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': str(error)})
    except Exception as error:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': f'Market context failed: {error}'})
