from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('accounts', '0006_account_monitor_credentials'),
        ('execution', '0010_rename_execution_b_account_6c8f5f_idx_execution_b_account_450fbd_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='NewsIntelligenceSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('snapshot_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('decision_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('symbol', models.CharField(db_index=True, max_length=32)),
                ('captured_at', models.DateTimeField(db_index=True)),
                ('provider_available', models.BooleanField(default=False)),
                ('news_state', models.CharField(default='DEGRADED', max_length=20)),
                ('fundamental_bias', models.CharField(default='UNCERTAIN', max_length=20)),
                ('event_risk', models.CharField(default='CLEAR', max_length=20)),
                ('execution_allowed', models.BooleanField(default=False)),
                ('technical_alignment', models.CharField(default='UNCERTAIN', max_length=32)),
                ('technical_conflict', models.BooleanField(default=False)),
                ('sentiment_score', models.FloatField(default=0.0)),
                ('sentiment_confidence', models.FloatField(default=0.0)),
                ('impact_score', models.FloatField(default=0.0)),
                ('reason_codes', models.JSONField(default=list)),
                ('events', models.JSONField(default=list)),
                ('reaction', models.JSONField(default=dict)),
                ('execution_conditions', models.JSONField(default=dict)),
                ('full_payload', models.JSONField(default=dict)),
                ('account', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='news_intelligence_snapshots', to='accounts.account')),
                ('orchestration_snapshot', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='news_snapshots', to='execution.orchestrationsnapshot')),
            ],
            options={'ordering': ['-captured_at']},
        ),
        migrations.CreateModel(
            name='NewsReactionObservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(db_index=True, max_length=32)),
                ('observed_at', models.DateTimeField(db_index=True)),
                ('expected_direction', models.CharField(default='UNKNOWN', max_length=12)),
                ('actual_direction', models.CharField(default='UNKNOWN', max_length=12)),
                ('reaction_state', models.CharField(default='UNCONFIRMED', max_length=20)),
                ('price_change', models.FloatField(blank=True, null=True)),
                ('volatility', models.CharField(default='UNKNOWN', max_length=20)),
                ('spread', models.FloatField(blank=True, null=True)),
                ('outcome_context', models.JSONField(default=dict)),
                ('news_snapshot', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='reaction_observations', to='news_intelligence.newsintelligencesnapshot')),
            ],
            options={'ordering': ['-observed_at']},
        ),
        migrations.AddIndex(model_name='newsintelligencesnapshot', index=models.Index(fields=['account', '-captured_at'], name='news_intel_account_captu_5a1d1d_idx')),
        migrations.AddIndex(model_name='newsintelligencesnapshot', index=models.Index(fields=['symbol', '-captured_at'], name='news_intel_symbol_captu_2c2e5f_idx')),
        migrations.AddIndex(model_name='newsintelligencesnapshot', index=models.Index(fields=['event_risk', '-captured_at'], name='news_intel_event_ri_5c4a30_idx')),
        migrations.AddIndex(model_name='newsreactionobservation', index=models.Index(fields=['symbol', '-observed_at'], name='news_react_symbol_obser_3a79da_idx')),
    ]