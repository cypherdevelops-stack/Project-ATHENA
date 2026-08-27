from datetime import datetime, timezone

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from backend.accounts.credentials import decrypt_password
from backend.accounts.handshake import DEFAULT_MT5_TERMINAL_PATH
from backend.accounts.models import Account
from backend.market.context import normalize_candles

from .detector import advance_poi_state, detect_features
from .models import PointOfInterest


def _poi_payload(poi):
    return {
        'id': poi.pk,
        'canonicalAsset': poi.canonical_asset,
        'brokerSymbol': poi.broker_symbol,
        'timeframe': poi.timeframe,
        'type': poi.poi_type,
        'formationTimestamp': poi.formation_timestamp.isoformat(),
        'lowerBound': poi.lower_bound,
        'upperBound': poi.upper_bound,
        'direction': poi.direction,
        'strength': poi.strength,
        'freshness': poi.freshness,
        'state': poi.state,
        'invalidationReason': poi.invalidation_reason,
        'reactionMetrics': poi.reaction_metrics,
    }


@login_required
@require_GET
def scan_view(request):
    timeframe = request.GET.get('timeframe', 'M5').upper()
    if timeframe not in {'M1', 'M5'}:
        return JsonResponse({'status': 'INVALID', 'reason': 'Only M1 and M5 scans are supported.'}, status=400)
    account = Account.objects.filter(user=request.user, pk=request.GET.get('accountId')).first()
    if account is None:
        account = Account.objects.filter(user=request.user, is_default=True, enabled=True).first() or Account.objects.filter(user=request.user, enabled=True).first()
    if account is None or not account.broker_symbol:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': 'No owned account has a discovered broker symbol.'}, status=422)

    initialized = False
    try:
        import MetaTrader5 as mt5
        password = decrypt_password(account.password_encrypted)
        initialized = mt5.initialize(path=account.terminal_path or DEFAULT_MT5_TERMINAL_PATH)
        if not initialized or not mt5.login(login=int(account.login), password=password, server=account.server):
            return JsonResponse({'status': 'UNAVAILABLE', 'reason': 'MT5 connection is unavailable.'}, status=422)
        timeframe_value = getattr(mt5, f'TIMEFRAME_{timeframe}')
        candles = normalize_candles(mt5.copy_rates_from_pos(account.broker_symbol, timeframe_value, 0, 200))
        features = detect_features(candles, timeframe)
        tick = mt5.symbol_info_tick(account.broker_symbol)
        current_price = float(getattr(tick, 'bid', 0) or candles[-1]['close']) if candles else 0
        pois = []
        for candidate in features['orderBlocks'] + features['fairValueGaps']:
            source_key = f"{candidate['type']}:{candidate['time']}:{candidate['lowerBound']}:{candidate['upperBound']}"
            state = advance_poi_state({**candidate, 'state': 'DETECTED'}, current_price)
            formed_at = datetime.fromtimestamp(candidate['time'], tz=timezone.utc)
            poi, _ = PointOfInterest.objects.update_or_create(
                account=account,
                timeframe=timeframe,
                source_key=source_key,
                defaults={
                    'canonical_asset': 'XAUUSD',
                    'broker_symbol': account.broker_symbol,
                    'poi_type': candidate['type'],
                    'formation_timestamp': formed_at,
                    'lower_bound': candidate['lowerBound'],
                    'upper_bound': candidate['upperBound'],
                    'direction': candidate['direction'],
                    'strength': candidate['strength'],
                    'state': state['state'],
                    'invalidation_reason': state.get('invalidationReason') or '',
                },
            )
            pois.append(_poi_payload(poi))
        return JsonResponse({'status': 'READY', 'accountId': account.pk, 'symbol': account.broker_symbol, 'timeframe': timeframe, 'features': features, 'pois': pois})
    except Exception as error:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': str(error)}, status=422)
    finally:
        if initialized:
            mt5.shutdown()
