from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [('accounts', '0007_account_equity')]
    operations = [
        migrations.CreateModel(
            name='DayTradingRiskState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(default='NORMAL', max_length=24)),
                ('consecutive_losses', models.PositiveIntegerField(default=0)),
                ('daily_risk_used', models.DecimalField(decimal_places=3, default=0, max_digits=8)),
                ('cooldown_until', models.DateTimeField(blank=True, null=True)),
                ('session_locked', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='day_trading_risk_state', to='accounts.account')),
            ],
        ),
    ]
