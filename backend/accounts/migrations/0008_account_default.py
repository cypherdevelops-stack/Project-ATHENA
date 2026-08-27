from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0007_account_equity')]

    operations = [
        migrations.AddField(
            model_name='account',
            name='is_default',
            field=models.BooleanField(default=False),
        ),
    ]