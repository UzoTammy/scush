from django.db import migrations


def consolidate_forward(apps, schema_editor):
    SalesCenter = apps.get_model('outlet', 'SalesCenter')

    # Front Gate becomes Trade Fair
    SalesCenter.objects.filter(name='Front Gate').update(name='Trade Fair')

    # Drop the other branches - Badagry and Trade Fair (ex Front Gate) remain
    SalesCenter.objects.exclude(name__in=['Trade Fair', 'Badagry']).delete()


def consolidate_backward(apps, schema_editor):
    SalesCenter = apps.get_model('outlet', 'SalesCenter')
    SalesCenter.objects.filter(name='Trade Fair').update(name='Front Gate')


class Migration(migrations.Migration):

    dependencies = [
        ('outlet', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(consolidate_forward, consolidate_backward),
    ]
