from unittest.mock import patch

from django.test import SimpleTestCase

from . import monitor


class AccountMonitorStartupTests(SimpleTestCase):
    def setUp(self):
        self.original_started = monitor._monitor_started
        monitor._monitor_started = False

    def tearDown(self):
        monitor._monitor_started = self.original_started

    def test_monitor_does_not_start_for_database_management_commands(self):
        with (
            patch.object(monitor.os.sys, 'argv', ['manage.py', 'makemigrations']),
            patch.dict(monitor.os.environ, {'ATHENA_DISABLE_MT5_MONITOR': '0'}),
            patch.object(monitor.threading, 'Thread') as thread,
        ):
            monitor.start_monitor()

        thread.assert_not_called()

    def test_monitor_still_starts_for_runserver(self):
        with (
            patch.object(monitor.os.sys, 'argv', ['manage.py', 'runserver']),
            patch.dict(monitor.os.environ, {'ATHENA_DISABLE_MT5_MONITOR': '0'}),
            patch.object(monitor.threading, 'Thread') as thread,
        ):
            monitor.start_monitor()

        thread.assert_called_once_with(
            target=monitor.monitor_loop,
            name='athena-mt5-monitor',
            daemon=True,
        )
        thread.return_value.start.assert_called_once_with()
