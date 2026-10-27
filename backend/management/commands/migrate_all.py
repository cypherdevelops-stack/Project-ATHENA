from django.conf import settings
from django.core.management import call_command
from django.db import connections
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Apply Django migrations to every configured ATHENA database.'

    def add_arguments(self, parser):
        parser.add_argument('app_label', nargs='?')
        parser.add_argument('migration_name', nargs='?')
        parser.add_argument(
            '--database',
            choices=tuple(settings.DATABASES),
            help='Migrate only the selected database alias.',
        )
        parser.add_argument(
            '--plan',
            action='store_true',
            help='Show the migration plan without applying it.',
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Exit with a non-zero status if migrations are pending.',
        )
        parser.add_argument('--fake', action='store_true')
        parser.add_argument('--fake-initial', action='store_true')
        parser.add_argument('--run-syncdb', action='store_true')
        parser.add_argument('--skip-checks', action='store_true')
        parser.add_argument('--prune', action='store_true')

    def handle(self, *args, **options):
        if options['migration_name'] and not options['app_label']:
            raise CommandError('A migration name requires an app label.')
        aliases = [options['database']] if options['database'] else list(settings.DATABASES)
        if len(settings.DATABASES) == 1:
            aliases = ['default']

        for alias in aliases:
            connection = connections[alias]
            original_host = connection.settings_dict['HOST']
            direct_host = original_host.replace('-pooler.', '.', 1)
            if direct_host != original_host:
                self.stdout.write(f'Using direct Neon endpoint for {alias}.')
            connection.settings_dict['HOST'] = direct_host
            connection.close()
            self.stdout.write(f'Applying migrations to {alias}...')
            migration_args = []
            if options['app_label']:
                migration_args.append(options['app_label'])
            if options['migration_name']:
                migration_args.append(options['migration_name'])
            try:
                call_command(
                    'migrate',
                    *migration_args,
                    database=alias,
                    interactive=False,
                    plan=options['plan'],
                    check=options['check'],
                    fake=options['fake'],
                    fake_initial=options['fake_initial'],
                    run_syncdb=options['run_syncdb'],
                    skip_checks=options['skip_checks'],
                    prune=options['prune'],
                    verbosity=options['verbosity'],
                    stdout=self.stdout,
                    stderr=self.stderr,
                )
            except CommandError as error:
                raise CommandError(f'Migration failed for database "{alias}": {error}') from error
            finally:
                connection.close()
                connection.settings_dict['HOST'] = original_host
