from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='user',
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name='trading_accounts',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]