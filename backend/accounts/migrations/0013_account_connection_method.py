from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0012_account_reconciliation_safe_and_more')]

    operations = [
        migrations.AddField(
            model_name='account',
            name='connection_method',
            field=models.CharField(
                choices=[('BROKER', 'Broker login'), ('METAAPI', 'MetaAPI')],
                default='BROKER',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='account',
            name='external_account_id',
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
