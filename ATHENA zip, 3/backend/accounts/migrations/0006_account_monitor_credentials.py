from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0005_account_handshake_capabilities')]

    operations = [
        migrations.AddField(model_name='account', name='terminal_path', field=models.CharField(blank=True, max_length=512)),
        migrations.AddField(model_name='account', name='password_encrypted', field=models.TextField(blank=True)),
    ]
