from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0011_account_allowed_strategies_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='last_reconciliation_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='reconciliation_safe',
            field=models.BooleanField(default=True),
        ),
    ]