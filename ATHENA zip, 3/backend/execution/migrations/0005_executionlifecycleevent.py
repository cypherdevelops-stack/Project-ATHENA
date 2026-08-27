from django.db import migrations, models
import django.db.models.deletion
import uuid
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0011_account_allowed_strategies_and_more'),
        ('execution', '0004_liveexecutionattempt_completed_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExecutionLifecycleEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('decision_id', models.UUIDField(db_index=True)),
                ('event_type', models.CharField(max_length=64)),
                ('state', models.CharField(max_length=32)),
                ('symbol', models.CharField(max_length=128)),
                ('payload', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(db_index=True, default=timezone.now)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='execution_lifecycle_events', to='accounts.account')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['account', '-created_at'], name='execution_e_account_3a3f4d_idx'),
                    models.Index(fields=['decision_id', '-created_at'], name='execution_e_decisio_9f1ac7_idx'),
                    models.Index(fields=['event_type', '-created_at'], name='execution_e_event_t_1a7b3f_idx'),
                ],
            },
        ),
    ]