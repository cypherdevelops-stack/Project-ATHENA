from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_account_user_many'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='platform',
            field=models.CharField(default='MT5', max_length=20),
        ),
        migrations.AddField(
            model_name='account',
            name='login',
            field=models.CharField(blank=True, max_length=120),
        ),
    ]