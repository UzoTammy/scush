from django.db import migrations, models
import django.db.models.deletion


def populate_categories(apps, schema_editor):
    Category = apps.get_model('stock', 'Category')
    Product = apps.get_model('stock', 'Product')
    Setting = apps.get_model('core', 'Setting')

    names = []
    try:
        names.extend(Setting.objects.get(key='product_category').list_value)
    except Setting.DoesNotExist:
        pass

    names.extend(
        Product.objects.exclude(category='').values_list('category', flat=True).distinct()
    )

    for name in dict.fromkeys(n for n in names if n):
        Category.objects.get_or_create(name=name)

    for product in Product.objects.all():
        if product.category:
            category, _ = Category.objects.get_or_create(name=product.category)
            product.category_new = category
            product.save(update_fields=['category_new'])

    Setting.objects.filter(key='product_category').delete()


def reverse_populate_categories(apps, schema_editor):
    Product = apps.get_model('stock', 'Product')

    for product in Product.objects.all():
        if product.category_new_id:
            product.category = product.category_new.name
            product.save(update_fields=['category'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_seed_settings'),
        ('stock', '0022_product_max_stock_level_product_min_stock_level_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name_plural': 'Categories',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='product',
            name='category_new',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='products', to='stock.category'),
        ),
        migrations.RunPython(populate_categories, reverse_populate_categories),
        migrations.RemoveField(
            model_name='product',
            name='category',
        ),
        migrations.RenameField(
            model_name='product',
            old_name='category_new',
            new_name='category',
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products', to='stock.category'),
        ),
    ]
