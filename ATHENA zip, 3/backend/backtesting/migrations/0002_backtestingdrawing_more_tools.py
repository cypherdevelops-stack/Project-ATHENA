from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('backtesting', '0001_initial')]

    operations = [
        migrations.AlterField(
            model_name='backtestingdrawing',
            name='drawing_type',
            field=models.CharField(
                choices=[
                    ('trendline', 'Trend line'), ('horizontal', 'Horizontal line'),
                    ('vertical', 'Vertical line'), ('ray', 'Ray'), ('rectangle', 'Rectangle'),
                    ('triangle', 'Triangle'), ('ellipse', 'Ellipse'),
                    ('long_position', 'Long position'), ('short_position', 'Short position'),
                ], max_length=16,
            ),
        ),
    ]
