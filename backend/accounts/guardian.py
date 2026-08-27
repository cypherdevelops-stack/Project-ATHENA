from .models import Account


def guardian_payload(account: Account):
    return {
        'state': account.guardian_state(),
        'dailyDrawdown': str(account.current_daily_drawdown),
        'dailyLimit': str(account.athena_safety_drawdown),
        'overallDrawdown': str(account.current_overall_drawdown),
        'overallLimit': str(account.max_overall_drawdown),
        'emergencyStop': account.emergency_stop,
    }
