from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0013_account_connection_method')]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='connection_method',
            field=models.CharField(
                choices=[('BROKER', 'Broker login'), ('METAAPI', 'MetaAPI'), ('DERIV', 'Deriv')],
                default='BROKER',
                max_length=16,
            ),
        ),
    ]
