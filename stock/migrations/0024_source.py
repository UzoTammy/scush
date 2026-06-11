from django.db import migrations, models
import django.db.models.deletion


def populate_sources(apps, schema_editor):
    Source = apps.get_model('stock', 'Source')
    Product = apps.get_model('stock', 'Product')
    Setting = apps.get_model('core', 'Setting')

    codes = []
    try:
        codes.extend(Setting.objects.get(key='product_source').list_value)
    except Setting.DoesNotExist:
        pass

    codes.extend(
        Product.objects.exclude(source='').values_list('source', flat=True).distinct()
    )

    for code in dict.fromkeys(c for c in codes if c):
        Source.objects.get_or_create(pk=code)

    for product in Product.objects.all():
        if product.source:
            source, _ = Source.objects.get_or_create(pk=product.source)
            product.source_new = source
            product.save(update_fields=['source_new'])

    Setting.objects.filter(key='product_source').delete()


def reverse_populate_sources(apps, schema_editor):
    Product = apps.get_model('stock', 'Product')

    for product in Product.objects.all():
        if product.source_new_id:
            product.source = product.source_new_id
            product.save(update_fields=['source'])


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0023_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='Source',
            fields=[
                ('code', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('label', models.CharField(blank=True, default='', max_length=100)),
                ('active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['code'],
            },
        ),
        migrations.AddField(
            model_name='product',
            name='source_new',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='products', to='stock.source'),
        ),
        migrations.RunPython(populate_sources, reverse_populate_sources),
        migrations.RemoveField(
            model_name='product',
            name='source',
        ),
        migrations.RenameField(
            model_name='product',
            old_name='source_new',
            new_name='source',
        ),
        migrations.AlterField(
            model_name='product',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products', to='stock.source'),
        ),
    ]
