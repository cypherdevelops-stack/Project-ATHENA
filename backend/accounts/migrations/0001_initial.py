from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_name', models.CharField(default='Primary account', max_length=120)),
                ('broker', models.CharField(blank=True, max_length=120)),
                ('server', models.CharField(blank=True, max_length=120)),
                ('account_type', models.CharField(choices=[('PERSONAL', 'Personal'), ('DEMO', 'Demo'), ('FUNDED', 'Funded')], default='DEMO', max_length=20)),
                ('base_currency', models.CharField(default='USD', max_length=3)),
                ('leverage', models.PositiveIntegerField(default=100)),
                ('enabled', models.BooleanField(default=False)),
                ('allowed_instruments', models.JSONField(default=list)),
                ('risk_per_trade', models.DecimalField(decimal_places=3, default=0.25, max_digits=6)),
                ('max_daily_drawdown', models.DecimalField(decimal_places=2, default=5.0, max_digits=6)),
                ('athena_safety_drawdown', models.DecimalField(decimal_places=2, default=3.0, max_digits=6)),
                ('max_overall_drawdown', models.DecimalField(decimal_places=2, default=10.0, max_digits=6)),
                ('max_concurrent_positions', models.PositiveIntegerField(default=1)),
                ('current_daily_drawdown', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('current_overall_drawdown', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('emergency_stop', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='trading_account', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
