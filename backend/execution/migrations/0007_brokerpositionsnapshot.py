from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ('execution', '0006_rename_execution_e_account_3a3f4d_idx_execution_e_account_e38398_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrokerPositionSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('decision_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('ticket', models.BigIntegerField()),
                ('symbol', models.CharField(max_length=128)),
                ('direction', models.CharField(max_length=10)),
                ('volume', models.DecimalField(decimal_places=8, max_digits=20)),
                ('price_open', models.DecimalField(decimal_places=8, max_digits=20)),
                ('stop_loss', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('take_profit', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('state', models.CharField(choices=[('ACTIVE', 'Active'), ('PARTIALLY_FILLED', 'Partially filled'), ('CLOSED', 'Closed'), ('MODIFIED', 'Modified'), ('RECONCILIATION_REQUIRED', 'Reconciliation required')], default='ACTIVE', max_length=32)),
                ('observed_at', models.DateTimeField(db_index=True, default=timezone.now)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='broker_position_snapshots', to='accounts.account')),
            ],
            options={'ordering': ['-observed_at']},
        ),
        migrations.AddConstraint(
            model_name='brokerpositionsnapshot',
            constraint=models.UniqueConstraint(fields=('account', 'ticket'), name='unique_broker_position_ticket'),
        ),
        migrations.AddIndex(
            model_name='brokerpositionsnapshot',
            index=models.Index(fields=['account', 'state', '-observed_at'], name='execution_b_account_6c8f5f_idx'),
        ),
        migrations.AddIndex(
            model_name='brokerpositionsnapshot',
            index=models.Index(fields=['symbol', 'state', '-observed_at'], name='execution_b_symbol_9f2f9b_idx'),
        ),
    ]