from django.conf import settings
from django.db.backends.signals import connection_created
from django.db.utils import OperationalError
import logging


logger = logging.getLogger(__name__)


def configure_sqlite_connection(sender, connection, **kwargs):
    """Enable concurrent reads and bounded lock waits for local SQLite."""
    if connection.vendor != 'sqlite':
        return
    cursor = connection.cursor()
    try:
        busy_timeout = int(getattr(settings, 'SQLITE_BUSY_TIMEOUT_MS', 5000))
        cursor.execute(f'PRAGMA busy_timeout = {busy_timeout}')
        try:
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.execute('PRAGMA synchronous=NORMAL')
        except OperationalError as error:
            if 'locked' not in str(error).lower():
                raise
            logger.warning('SQLite WAL setup deferred because the database is busy: %s', error)
    finally:
        cursor.close()


connection_created.connect(configure_sqlite_connection)


class MigrationRouter:
    """
    Route normal ORM traffic through the default connection.

    When a separate 'direct' database is configured, keep migrations there; for
    SQLite (the default local setup) allow migrations on the default database.
    """

    def db_for_read(self, model, **hints):
        return 'default'

    def db_for_write(self, model, **hints):
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        direct_db = settings.DATABASES.get('direct')
        if direct_db is None:
            return db == 'default'
        return db == 'direct'
