from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0006_account_monitor_credentials')]

    operations = [
        migrations.AddField(
            model_name='account',
            name='equity',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
    ]