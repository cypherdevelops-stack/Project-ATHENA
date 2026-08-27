from __future__ import annotations

import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from backend.accounts.models import Account
from backend.market.service import market_data_service, MarketDataError
from backend.market.regime import evaluate_regime
from backend.execution.executioner_service import generate_orchestrated_execution_analysis
from backend.execution.xgboost_engine import get_active_xgboost_engine
from backend.execution.models import OrchestratorSessionLog
from backend.execution.snapshot_service import persist_orchestration_snapshot
from backend.execution.paper_orchestration import execute_paper_decision
from backend.execution.demo_execution import DemoExecutionError, execute_automatic_decision
from backend.execution.live_engine import LiveExecutionError
from backend.execution.reconciliation import reconcile_live_positions
from backend.stream.console_renderer import ConsoleStreamRenderer


class Command(BaseCommand):
    help = 'Monitor ATHENA orchestrator in real-time, persisting snapshots and decisions.'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--account-id',
            type=int,
            required=True,
            help='Account ID to monitor',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Update interval in seconds (default: 60)',
        )
        parser.add_argument(
            '--duration',
            type=int,
            default=3600,
            help='Duration to monitor in seconds (default: 3600 = 1 hour). 0 = infinite',
        )
        parser.add_argument(
            '--no-render',
            action='store_true',
            help='Disable console rendering (for background operation)',
        )
        parser.add_argument(
            '--paper',
            action='store_true',
            help='Open approved orchestrator decisions in the paper engine.',
        )
        parser.add_argument(
            '--automatic',
            action='store_true',
            help='Submit approved decisions through the automatic account policy.',
        )
    
    def handle(self, *args, **options):
        account_id = options['account_id']
        interval = options['interval']
        duration = options['duration']
        render_console = not options['no_render']
        paper_mode = options['paper']
        automatic_mode = options['automatic']
        if paper_mode and automatic_mode:
            raise CommandError('--paper and --automatic cannot be used together')
        
        # Fetch account
        try:
            account = Account.objects.get(pk=account_id)
        except Account.DoesNotExist:
            raise CommandError(f'Account {account_id} does not exist')
        
        if not account.enabled:
            raise CommandError(f'Account {account_id} is disabled')
        
        if not account.broker_symbol:
            raise CommandError(f'Account {account_id} has no broker symbol')
        if automatic_mode and account.live_execution_mode != 'AUTOMATIC':
            raise CommandError('Automatic monitoring requires the account AUTOMATIC execution policy')
        if automatic_mode and account.account_type != Account.AccountType.DEMO:
            raise CommandError('Automatic monitoring is restricted to demo accounts')
        if automatic_mode and not account.allowed_strategies:
            raise CommandError('Automatic monitoring requires at least one allowed strategy')
        if automatic_mode and not account.allowed_instruments:
            raise CommandError('Automatic monitoring requires an explicit instrument allow-list')
        if automatic_mode and account.canonical_asset not in account.allowed_instruments:
            raise CommandError('Automatic monitoring symbol is outside the account instrument policy')
        if automatic_mode and not account.max_live_orders_per_day:
            raise CommandError('Automatic monitoring requires a nonzero daily order limit')
        if automatic_mode and not account.max_live_risk_per_day:
            raise CommandError('Automatic monitoring requires a nonzero daily risk limit')
        if automatic_mode and not account.max_order_value:
            raise CommandError('Automatic monitoring requires a nonzero order-value limit')
        if automatic_mode and not account.require_fresh_decision_seconds:
            raise CommandError('Automatic monitoring requires a fresh-decision window')
        
        symbol = account.broker_symbol
        self.stdout.write(self.style.SUCCESS(f'Starting orchestrator monitoring for {symbol}'))
        
        # Create session log
        session = OrchestratorSessionLog.objects.create(
            account=account,
            symbol=symbol,
            notes=f'CLI monitoring session. Interval: {interval}s',
        )
        
        renderer = ConsoleStreamRenderer(write=self.stdout.write) if render_console else None
        start_time = timezone.now()
        
        try:
            iteration = 0
            while True:
                # Check duration limit
                if duration > 0:
                    elapsed = (timezone.now() - start_time).total_seconds()
                    if elapsed >= duration:
                        self.stdout.write(self.style.SUCCESS(f'\nMonitoring duration ({duration}s) completed'))
                        break
                
                iteration += 1
                loop_start = time.time()
                
                try:
                    # Fetch multi-timeframe data
                    data = market_data_service.fetch(
                        account,
                        timeframes=('M1', 'M5', 'M15', 'H1', 'H4')
                    )
                    
                    regime_ctx = evaluate_regime(data.candles.get('H1', [])).as_dict()
                    
                    # Generate orchestrated analysis
                    analysis = generate_orchestrated_execution_analysis(
                        account=account,
                        m5_candles=data.candles.get('M5', []),
                        m1_candles=data.candles.get('M1', []),
                        m15_candles=data.candles.get('M15', []),
                        h1_candles=data.candles.get('H1', []),
                        h4_candles=data.candles.get('H4', []),
                        current_price_data=data.snapshot.as_dict(),
                        regime_context=regime_ctx,
                        ml_engine=get_active_xgboost_engine(),
                    )
                    
                    # Render to console if enabled
                    if renderer and analysis.get('status') != 'ERROR':
                        renderer.render_orchestrated_analysis(analysis)
                    
                    # Persist snapshot
                    snapshot = self._save_snapshot(account, symbol, analysis)
                    if paper_mode and snapshot:
                        paper_result = execute_paper_decision(
                            account=account,
                            analysis=analysis,
                            decision_id=snapshot.decision_id,
                            quote=data.snapshot.as_dict(),
                        )
                        if paper_result.get('status') == 'OPENED':
                            self.stdout.write(self.style.SUCCESS(
                                f"Paper position opened: {paper_result.get('positionId')}"
                            ))
                    if automatic_mode and snapshot:
                        reconciliation = reconcile_live_positions(account=account)
                        if reconciliation.get('status') == 'UNSAFE':
                            self.stdout.write(self.style.ERROR(
                                f"Reconciliation unsafe; automatic submission skipped: {reconciliation.get('reason', reconciliation.get('missingAttempts'))}"
                            ))
                            snapshot = None
                    if automatic_mode and snapshot:
                        try:
                            automatic_result = execute_automatic_decision(
                                account=account,
                                snapshot=snapshot,
                            )
                            if automatic_result.get('status') == 'ACCEPTED':
                                self.stdout.write(self.style.SUCCESS(
                                    f"Automatic order accepted: {automatic_result.get('order')}"
                                ))
                            elif automatic_result.get('status') != 'REJECTED':
                                self.stdout.write(self.style.WARNING(
                                    f"Automatic decision result: {automatic_result.get('status')}"
                                ))
                        except (DemoExecutionError, LiveExecutionError) as error:
                            self.stdout.write(self.style.ERROR(f'Automatic execution rejected: {error}'))
                    
                    # Update session
                    session.snapshots_count += 1
                    orchestration = analysis.get('orchestration', {})
                    decision = orchestration.get('decision', {}).get('action', '')
                    if decision.startswith('SCALP'):
                        session.scalping_approvals += 1
                    elif decision.startswith('DAY'):
                        session.day_trading_develops += 1
                    session.save()
                    
                except MarketDataError as e:
                    self.stdout.write(self.style.ERROR(f'Market data error: {e}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Analysis error: {e}'))
                
                # Measure latency and sleep
                loop_duration = time.time() - loop_start
                session.avg_decision_latency_ms = (
                    (session.avg_decision_latency_ms * (iteration - 1) + loop_duration * 1000) / iteration
                )
                
                sleep_time = max(0, interval - loop_duration)
                if sleep_time > 0:
                    time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nMonitoring stopped by user'))
        
        finally:
            # Finalize session
            session.ended_at = timezone.now()
            session.save()
            
            self.stdout.write(self.style.SUCCESS(
                f'\nSession complete:\n'
                f'  Duration: {session.duration_str}\n'
                f'  Snapshots: {session.snapshots_count}\n'
                f'  Scalping approvals: {session.scalping_approvals}\n'
                f'  Day trading develops: {session.day_trading_develops}\n'
                f'  Avg latency: {session.avg_decision_latency_ms:.1f}ms\n'
            ))
    
    def _save_snapshot(self, account: Account, symbol: str, analysis: dict):
        """Persist orchestration snapshot to database."""
        return persist_orchestration_snapshot(account=account, analysis=analysis)
