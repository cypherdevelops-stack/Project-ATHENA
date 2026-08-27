from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from backend.accounts.credentials import decrypt_password
from backend.accounts.handshake import DEFAULT_MT5_TERMINAL_PATH
from backend.accounts.models import Account
from backend.market.context import normalize_candles
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

    initialized = False
    try:
        import MetaTrader5 as mt5
        password = decrypt_password(account.password_encrypted)
        initialized = mt5.initialize(path=account.terminal_path or DEFAULT_MT5_TERMINAL_PATH)
        if not initialized or not mt5.login(login=int(account.login), password=password, server=account.server):
            return JsonResponse({'status': 'BLOCKED', 'reasonCodes': ['BROKER_CONNECTION_UNAVAILABLE'], 'candidates': []}, status=422)
        m1_rates = mt5.copy_rates_from_pos(account.broker_symbol, mt5.TIMEFRAME_M1, 0, 200)
        m5_rates = mt5.copy_rates_from_pos(account.broker_symbol, mt5.TIMEFRAME_M5, 0, 200)
        m1_features = detect_features(normalize_candles(m1_rates), 'M1')
        m5_features = detect_features(normalize_candles(m5_rates), 'M5')
        if m1_features.get('events'):
            m1_features['latestTime'] = m1_features['events'][-1]['time']
        if m5_features.get('events'):
            m5_features['latestTime'] = m5_features['events'][-1]['time']
        tick = mt5.symbol_info_tick(account.broker_symbol)
        current_price = float(getattr(tick, 'bid', 0) or 0)
        candidates = generate_scalping_candidates(account=account, broker_symbol=account.broker_symbol, current_price=current_price, m1_features=m1_features, m5_features=m5_features)
        decision_stream = build_decision_stream(candidates=candidates, m1_features=m1_features, m5_features=m5_features, current_price=current_price)
        return JsonResponse({'status': 'READY', 'accountId': account.pk, 'symbol': account.broker_symbol, 'm1': m1_features, 'm5': m5_features, 'candidates': candidates, 'decisionStream': decision_stream})
    except Exception as error:
        return JsonResponse({'status': 'BLOCKED', 'reasonCodes': ['SCALPING_SCAN_FAILED'], 'reason': str(error), 'candidates': []}, status=422)
    finally:
        if initialized:
            mt5.shutdown()
