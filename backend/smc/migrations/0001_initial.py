from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [('accounts', '0007_account_equity')]
    operations = [
        migrations.CreateModel(
            name='PointOfInterest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('canonical_asset', models.CharField(max_length=32)),
                ('broker_symbol', models.CharField(max_length=128)),
                ('timeframe', models.CharField(max_length=4)),
                ('source_key', models.CharField(max_length=160)),
                ('poi_type', models.CharField(max_length=12)),
                ('formation_timestamp', models.DateTimeField()),
                ('lower_bound', models.FloatField()),
                ('upper_bound', models.FloatField()),
                ('direction', models.CharField(max_length=12)),
                ('strength', models.FloatField(default=0)),
                ('freshness', models.FloatField(default=1)),
                ('state', models.CharField(default='DETECTED', max_length=20)),
                ('invalidation_reason', models.CharField(blank=True, max_length=80)),
                ('reaction_metrics', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='points_of_interest', to='accounts.account')),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('account', 'timeframe', 'source_key'), name='unique_account_timeframe_poi')]},
        ),
    ]
