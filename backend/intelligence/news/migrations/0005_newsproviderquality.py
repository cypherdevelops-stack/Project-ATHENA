from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [('news_intelligence', '0004_newsamefrecord')]

    operations = [
        migrations.CreateModel(
            name='NewsProviderQuality',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider_name', models.CharField(max_length=64)),
                ('observed_at', models.DateTimeField(db_index=True, default=timezone.now)),
                ('available', models.BooleanField(default=False)),
                ('latency_ms', models.FloatField(blank=True, null=True)),
                ('item_count', models.PositiveIntegerField(default=0)),
                ('duplicate_count', models.PositiveIntegerField(default=0)),
                ('source_agreement', models.FloatField(blank=True, null=True)),
                ('error', models.TextField(blank=True)),
            ],
            options={'ordering': ['-observed_at']},
        ),
        migrations.AddIndex(model_name='newsproviderquality', index=models.Index(fields=['provider_name', '-observed_at'], name='news_provider_name_obser_8dcd6e_idx')),
    ]