from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from backend.accounts.models import Account

from .engine import evaluate_day_trading_state
from .models import DayTradingRiskState


@login_required
@require_GET
def state_view(request):
    account = Account.objects.filter(user=request.user, pk=request.GET.get('accountId')).first()
    if account is None:
        account = Account.objects.filter(user=request.user, is_default=True, enabled=True).first() or Account.objects.filter(user=request.user, enabled=True).first()
    if account is None:
        return JsonResponse({'status': 'BLOCKED', 'reasonCodes': ['ACCOUNT_UNAVAILABLE']}, status=422)
    risk_state, _ = DayTradingRiskState.objects.get_or_create(account=account)
    evaluation = evaluate_day_trading_state(account, risk_state)
    return JsonResponse({
        'status': evaluation['decisionState'],
        'accountId': account.pk,
        'module': 'DAY_TRADING',
        'riskState': {
            'state': risk_state.state,
            'consecutiveLosses': risk_state.consecutive_losses,
            'dailyRiskUsed': str(risk_state.daily_risk_used),
            'cooldownUntil': risk_state.cooldown_until.isoformat() if risk_state.cooldown_until else None,
            'sessionLocked': risk_state.session_locked,
        },
        'reasonCodes': evaluation['reasonCodes'],
    })
