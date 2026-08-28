from __future__ import annotations

import time

from django.core.management.base import BaseCommand, CommandError

from backend.intelligence.news.tasks import poll_enabled_accounts


class Command(BaseCommand):
    help = 'Poll configured news and calendar providers without submitting trades.'

    def add_arguments(self, parser):
        parser.add_argument('--account-id', type=int)
        parser.add_argument('--interval', type=int, default=30)
        parser.add_argument('--duration', type=int, default=0, help='Seconds to run; 0 means continuous.')

    def handle(self, *args, **options):
        interval = max(options['interval'], 1)
        duration = max(options['duration'], 0)
        started = time.monotonic()
        while True:
            results = poll_enabled_accounts(account_id=options.get('account_id'))
            for result in results:
                self.stdout.write(f"{result['symbol']}: {result['status']} / {result['newsRisk']} / {result['reason']}")
            if duration and time.monotonic() - started >= duration:
                return
            if not results:
                raise CommandError('No enabled trading accounts were found.')
            time.sleep(interval)