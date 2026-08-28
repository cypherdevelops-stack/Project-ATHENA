from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('news_intelligence', '0002_adaptivenewsstatistic')]

    operations = [
        migrations.CreateModel(
            name='NewsMarketSample',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phase', models.CharField(choices=[('PRE', 'Pre-event'), ('POST', 'Post-event')], max_length=12)),
                ('captured_at', models.DateTimeField(db_index=True)),
                ('bid', models.FloatField(blank=True, null=True)),
                ('ask', models.FloatField(blank=True, null=True)),
                ('spread', models.FloatField(blank=True, null=True)),
                ('volatility', models.CharField(default='UNKNOWN', max_length=20)),
                ('metadata', models.JSONField(default=dict)),
                ('news_snapshot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='market_samples', to='news_intelligence.newsintelligencesnapshot')),
            ],
            options={'ordering': ['captured_at']},
        ),
        migrations.AddIndex(
            model_name='newsmarketsample',
            index=models.Index(fields=['news_snapshot', 'phase', '-captured_at'], name='news_market_snapshot_phase_idx'),
        ),
    ]