from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('news_intelligence', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='AdaptiveNewsStatistic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=32)),
                ('category', models.CharField(default='OTHER', max_length=32)),
                ('regime', models.CharField(default='UNKNOWN', max_length=32)),
                ('source_class', models.CharField(default='unknown', max_length=32)),
                ('observations', models.PositiveIntegerField(default=0)),
                ('confirmed_reactions', models.PositiveIntegerField(default=0)),
                ('contrary_reactions', models.PositiveIntegerField(default=0)),
                ('mean_price_change', models.FloatField(default=0.0)),
                ('mean_sentiment_confidence', models.FloatField(default=0.0)),
                ('last_observed_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-updated_at']},
        ),
        migrations.AddConstraint(
            model_name='adaptivenewsstatistic',
            constraint=models.UniqueConstraint(fields=('symbol', 'category', 'regime', 'source_class'), name='unique_adaptive_news_context'),
        ),
        migrations.AddIndex(
            model_name='adaptivenewsstatistic',
            index=models.Index(fields=['symbol', 'category', 'regime'], name='news_adapt_symbol_categor_4c18d2_idx'),
        ),
    ]