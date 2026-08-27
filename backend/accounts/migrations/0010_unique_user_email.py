from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0009_backfill_default_accounts'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE UNIQUE INDEX unique_auth_user_email_ci ON auth_user (LOWER(email));',
            reverse_sql='DROP INDEX unique_auth_user_email_ci;',
        ),
    ]
