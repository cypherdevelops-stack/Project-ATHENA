from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('execution', '0008_executionintent'),
    ]

    operations = [
        migrations.AddField(
            model_name='liveexecutionattempt',
            name='intent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='execution_attempts', to='execution.executionintent'),
        ),
    ]