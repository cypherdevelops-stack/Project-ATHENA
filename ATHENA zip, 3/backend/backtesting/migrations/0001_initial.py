from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ('accounts', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='BacktestingDrawing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=128)),
                ('timeframe', models.CharField(max_length=8)),
                ('drawing_type', models.CharField(choices=[('trendline', 'Trend line'), ('horizontal', 'Horizontal line'), ('vertical', 'Vertical line'), ('ray', 'Ray'), ('rectangle', 'Rectangle')], max_length=16)),
                ('start', models.JSONField()),
                ('end', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='backtesting_drawings', to='accounts.account')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='backtesting_drawings', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
