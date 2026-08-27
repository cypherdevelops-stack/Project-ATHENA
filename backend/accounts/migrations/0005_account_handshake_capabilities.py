from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('accounts', '0004_account_market_discovery')]

    operations = [
        migrations.AddField(model_name='account', name='balance', field=models.DecimalField(decimal_places=2, default=0, max_digits=20)),
        migrations.AddField(model_name='account', name='account_mode', field=models.CharField(blank=True, max_length=32)),
        migrations.AddField(model_name='account', name='trade_allowed', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='account', name='terminal_connected', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='account', name='last_handshake_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='account', name='handshake_status', field=models.CharField(blank=True, max_length=32)),
        migrations.CreateModel(
            name='AccountInstrumentCapability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('canonical_asset', models.CharField(max_length=32)),
                ('broker_symbol', models.CharField(max_length=128)),
                ('symbol_visible', models.BooleanField(default=False)),
                ('symbol_selected', models.BooleanField(default=False)),
                ('trade_mode', models.IntegerField(blank=True, null=True)),
                ('execution_mode', models.IntegerField(blank=True, null=True)),
                ('filling_modes', models.JSONField(default=list)),
                ('order_modes', models.JSONField(default=list)),
                ('digits', models.IntegerField(blank=True, null=True)),
                ('point', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('tick_size', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('volume_min', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('volume_max', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('volume_step', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('stops_level', models.IntegerField(blank=True, null=True)),
                ('freeze_level', models.IntegerField(blank=True, null=True)),
                ('contract_size', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('last_discovered_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='instrument_capabilities', to='accounts.account')),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('account', 'canonical_asset', 'broker_symbol'), name='unique_account_asset_symbol')]},
        ),
    ]