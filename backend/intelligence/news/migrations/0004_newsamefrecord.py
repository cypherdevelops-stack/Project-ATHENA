from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [('news_intelligence', '0003_newsmarketsample')]

    operations = [
        migrations.CreateModel(
            name='NewsAMEFRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(db_index=True, default=timezone.now)),
                ('event_context', models.JSONField(default=dict)),
                ('asset_context', models.JSONField(default=dict)),
                ('technical_context', models.JSONField(default=dict)),
                ('reaction_context', models.JSONField(default=dict)),
                ('execution_context', models.JSONField(default=dict)),
                ('trade_outcome', models.JSONField(default=dict)),
                ('news_snapshot', models.OneToOneField(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='amef_record', to='news_intelligence.newsintelligencesnapshot')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]