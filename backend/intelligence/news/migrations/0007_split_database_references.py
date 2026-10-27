from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('news_intelligence', '0006_rename_news_adapt_symbol_categor_4c18d2_idx_news_intell_symbol_0fc8a5_idx_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='newsintelligencesnapshot',
            old_name='account',
            new_name='account_id',
        ),
        migrations.AlterField(
            model_name='newsintelligencesnapshot',
            name='account_id',
            field=models.BigIntegerField(db_column='account_id', db_index=True),
        ),
        migrations.RemoveField(
            model_name='newsintelligencesnapshot',
            name='orchestration_snapshot',
        ),
        migrations.RenameField(
            model_name='newsreactionobservation',
            old_name='news_snapshot',
            new_name='news_snapshot_id',
        ),
        migrations.AlterField(
            model_name='newsreactionobservation',
            name='news_snapshot_id',
            field=models.BigIntegerField(db_column='news_snapshot_id', db_index=True),
        ),
        migrations.RenameField(
            model_name='newsamefrecord',
            old_name='news_snapshot',
            new_name='news_snapshot_id',
        ),
        migrations.AlterField(
            model_name='newsamefrecord',
            name='news_snapshot_id',
            field=models.BigIntegerField(db_column='news_snapshot_id', unique=True),
        ),
    ]
