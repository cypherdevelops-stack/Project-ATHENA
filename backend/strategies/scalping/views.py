from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from backend.accounts.models import Account
from backend.market.service import market_data_service
from backend.smc.detector import detect_features

from .candidates import build_decision_stream, generate_scalping_candidates


@login_required
@require_GET
def candidates_view(request):
    account = Account.objects.filter(user=request.user, pk=request.GET.get('accountId')).first()
    if account is None:
        account = Account.objects.filter(user=request.user, is_default=True, enabled=True).first() or Account.objects.filter(user=request.user, enabled=True).first()
    if account is None or not account.broker_symbol:
        return JsonResponse({'status': 'BLOCKED', 'reasonCodes': ['BROKER_SYMBOL_UNAVAILABLE'], 'candidates': []}, status=422)
    try:
        data = market_data_service.fetch(account, timeframes=('M1', 'M5'))
        m1_candles = data.candles['M1']
        m5_candles = data.candles['M5']
        m1_features = detect_features(m1_candles, 'M1')
        m5_features = detect_features(m5_candles, 'M5')
        if m1_features.get('events'):
            m1_features['latestTime'] = m1_features['events'][-1]['time']
        if m5_features.get('events'):
            m5_features['latestTime'] = m5_features['events'][-1]['time']
        current_price = data.snapshot.bid
        candidates = generate_scalping_candidates(
            account=account,
            broker_symbol=account.broker_symbol,
            current_price=current_price,
            m1_features=m1_features,
            m5_features=m5_features,
            m1_candles=m1_candles,
            m5_candles=m5_candles,
            context={
                'execution_allowed': data.data_quality['execution_allowed'],
                'marketDataQuality': data.data_quality,
            },
        )
        decision_stream = build_decision_stream(candidates=candidates, m1_features=m1_features, m5_features=m5_features, current_price=current_price)
        return JsonResponse({
            'status': 'READY',
            'accountId': account.pk,
            'symbol': account.broker_symbol,
            'm1': m1_features,
            'm5': m5_features,
            'candidates': candidates,
            'decisionStream': decision_stream,
            'marketDataQuality': data.data_quality,
        })
    except Exception as error:
        return JsonResponse({'status': 'BLOCKED', 'reasonCodes': ['SCALPING_SCAN_FAILED'], 'reason': str(error), 'candidates': []}, status=422)
