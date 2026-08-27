from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('journal', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='journalsession',
            name='market_session',
            field=models.CharField(default='UNKNOWN', max_length=20),
        ),
    ]