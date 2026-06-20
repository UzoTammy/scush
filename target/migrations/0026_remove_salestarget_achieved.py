from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('target', '0025_redesign'),
    ]

    operations = [
        migrations.RemoveField(model_name='salestarget', name='achieved_currency'),
        migrations.RemoveField(model_name='salestarget', name='achieved'),
    ]
