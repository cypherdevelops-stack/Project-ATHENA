from django.db import migrations


def infer_session(apps, schema_editor):
    JournalSession = apps.get_model('journal', 'JournalSession')
    for session in JournalSession.objects.filter(market_session='UNKNOWN').iterator():
        hour = session.started_at.hour
        if 13 <= hour < 21:
            market_session = 'NEW_YORK'
        elif 8 <= hour < 16:
            market_session = 'LONDON'
        elif hour < 9:
            market_session = 'TOKYO'
        else:
            market_session = 'UNKNOWN'
        if market_session != 'UNKNOWN':
            JournalSession.objects.filter(pk=session.pk).update(market_session=market_session)


class Migration(migrations.Migration):
    dependencies = [('journal', '0002_journalsession_market_session')]
    operations = [migrations.RunPython(infer_session, migrations.RunPython.noop)]
