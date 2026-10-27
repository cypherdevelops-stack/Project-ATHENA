from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('backtesting', '0008_replaydecision'),
    ]

    operations = [
        migrations.RenameField(
            model_name='backtestingdrawing',
            old_name='user',
            new_name='user_id',
        ),
        migrations.AlterField(
            model_name='backtestingdrawing',
            name='user_id',
            field=models.BigIntegerField(db_column='user_id', db_index=True),
        ),
        migrations.RenameField(
            model_name='backtestingdrawing',
            old_name='account',
            new_name='account_id',
        ),
        migrations.AlterField(
            model_name='backtestingdrawing',
            name='account_id',
            field=models.BigIntegerField(db_column='account_id', db_index=True),
        ),
        migrations.RenameField(
            model_name='historicalcandle',
            old_name='user',
            new_name='user_id',
        ),
        migrations.AlterField(
            model_name='historicalcandle',
            name='user_id',
            field=models.BigIntegerField(db_column='user_id', db_index=True),
        ),
        migrations.RenameField(
            model_name='historicalcandle',
            old_name='account',
            new_name='account_id',
        ),
        migrations.AlterField(
            model_name='historicalcandle',
            name='account_id',
            field=models.BigIntegerField(db_column='account_id', db_index=True),
        ),
        migrations.RenameField(
            model_name='historicaldataset',
            old_name='user',
            new_name='user_id',
        ),
        migrations.AlterField(
            model_name='historicaldataset',
            name='user_id',
            field=models.BigIntegerField(db_column='user_id', db_index=True),
        ),
        migrations.RenameField(
            model_name='historicaldataset',
            old_name='account',
            new_name='account_id',
        ),
        migrations.AlterField(
            model_name='historicaldataset',
            name='account_id',
            field=models.BigIntegerField(db_column='account_id', db_index=True),
        ),
        migrations.RenameField(
            model_name='replaysession',
            old_name='user',
            new_name='user_id',
        ),
        migrations.AlterField(
            model_name='replaysession',
            name='user_id',
            field=models.BigIntegerField(db_column='user_id', db_index=True),
        ),
        migrations.RenameField(
            model_name='replaysession',
            old_name='account',
            new_name='account_id',
        ),
        migrations.AlterField(
            model_name='replaysession',
            name='account_id',
            field=models.BigIntegerField(db_column='account_id', db_index=True),
        ),
    ]
