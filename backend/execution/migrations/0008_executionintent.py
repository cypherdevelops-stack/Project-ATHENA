from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ('execution', '0007_brokerpositionsnapshot'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExecutionIntent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('decision_id', models.UUIDField(db_index=True, unique=True)),
                ('strategy', models.CharField(max_length=20)),
                ('direction', models.CharField(max_length=10)),
                ('symbol', models.CharField(max_length=128)),
                ('setup', models.JSONField(default=dict)),
                ('status', models.CharField(choices=[('QUEUED', 'Queued'), ('SUBMITTING', 'Submitting'), ('ACCEPTED', 'Accepted'), ('REJECTED', 'Rejected'), ('EXPIRED', 'Expired'), ('INVALIDATED', 'Invalidated')], default='QUEUED', max_length=20)),
                ('created_at', models.DateTimeField(db_index=True, default=timezone.now)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('invalidation_reason', models.TextField(blank=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='execution_intents', to='accounts.account')),
                ('snapshot', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='execution_intent', to='execution.orchestrationsnapshot')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='executionintent',
            index=models.Index(fields=['account', 'status', '-created_at'], name='execution_i_account_4b9a27_idx'),
        ),
        migrations.AddIndex(
            model_name='executionintent',
            index=models.Index(fields=['symbol', 'status', '-created_at'], name='execution_i_symbol_5bb19d_idx'),
        ),
    ]