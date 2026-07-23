from django.db import migrations, models
import django.db.models.deletion


def populate_positions(apps, schema_editor):
    Position = apps.get_model('staff', 'Position')
    Employee = apps.get_model('staff', 'Employee')
    Setting = apps.get_model('core', 'Setting')

    names = []
    try:
        names.extend(Setting.objects.get(key='positions').list_value)
    except Setting.DoesNotExist:
        pass

    names.extend(
        Employee.objects.exclude(position='').exclude(position__isnull=True)
        .values_list('position', flat=True).distinct()
    )

    for name in dict.fromkeys(n.strip() for n in names if n and n.strip()):
        Position.objects.get_or_create(name=name)

    for employee in Employee.objects.exclude(position='').exclude(position__isnull=True):
        position, _ = Position.objects.get_or_create(name=employee.position.strip())
        employee.position_new_id = position.id
        employee.save(update_fields=['position_new'])

    Setting.objects.filter(key='positions').delete()


def reverse_populate_positions(apps, schema_editor):
    Employee = apps.get_model('staff', 'Employee')

    for employee in Employee.objects.all():
        if employee.position_new_id:
            employee.position = employee.position_new.name
            employee.save(update_fields=['position'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_seed_settings'),
        ('staff', '0057_equity_pool'),
    ]

    operations = [
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='employee',
            name='position_new',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT,
                                     related_name='employees', to='staff.position'),
        ),
        migrations.RunPython(populate_positions, reverse_populate_positions),
        migrations.RemoveField(
            model_name='employee',
            name='position',
        ),
        migrations.RenameField(
            model_name='employee',
            old_name='position_new',
            new_name='position',
        ),
        migrations.AlterField(
            model_name='employee',
            name='position',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT,
                                     related_name='employees', to='staff.position'),
        ),
    ]
