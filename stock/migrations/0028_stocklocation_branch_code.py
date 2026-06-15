import django.db.models.deletion
from django.db import migrations, models


def assign_branch_forward(apps, schema_editor):
    StockLocation = apps.get_model('stock', 'StockLocation')
    SalesCenter = apps.get_model('outlet', 'SalesCenter')
    unassigned = StockLocation.objects.filter(branch__isnull=True)
    if unassigned.exists():
        trade_fair = SalesCenter.objects.get(name='Trade Fair')
        unassigned.update(branch=trade_fair)


def assign_branch_backward(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('outlet', '0002_consolidate_branches'),
        ('stock', '0027_stocklocation_source_contact_person_source_email_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='stocklocation',
            name='code',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='stocklocation',
            name='branch',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='material_centers', to='outlet.salescenter'),
        ),
        migrations.RunPython(assign_branch_forward, assign_branch_backward),
        migrations.AlterField(
            model_name='stocklocation',
            name='branch',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='material_centers', to='outlet.salescenter'),
        ),
        migrations.AlterModelOptions(
            name='stocklocation',
            options={'ordering': ['branch__name', 'name']},
        ),
    ]
