from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_account_credentials'),
    ]

    operations = [
        migrations.AddField(model_name='account', name='canonical_asset', field=models.CharField(blank=True, max_length=32)),
        migrations.AddField(model_name='account', name='broker_symbol', field=models.CharField(blank=True, max_length=128)),
        migrations.AddField(model_name='account', name='market_discovery', field=models.JSONField(default=dict)),
    ]