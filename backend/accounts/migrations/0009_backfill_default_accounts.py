from django.db import migrations


def set_defaults(apps, schema_editor):
    Account = apps.get_model('accounts', 'Account')
    user_ids = Account.objects.values_list('user_id', flat=True).distinct()
    for user_id in user_ids:
        if not Account.objects.filter(user_id=user_id, is_default=True).exists():
            account = Account.objects.filter(user_id=user_id).order_by('pk').first()
            if account:
                Account.objects.filter(pk=account.pk).update(is_default=True)


class Migration(migrations.Migration):
    dependencies = [('accounts', '0008_account_default')]
    operations = [migrations.RunPython(set_defaults, migrations.RunPython.noop)]
