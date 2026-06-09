from django.db import migrations


PRODUCT_LISTS = [
    ('product_source',       'Product Sources',    'product-source'),
    ('product_category',     'Product Categories', 'product-category'),
    ('product_units',        'Product Units',      'product-units'),
    ('product_packs',        'Pack Sizes',         'product-packs'),
    ('product_states',       'Product States',     'product-states'),
    ('product_volume_units', 'Volume Units',       'product-volume-units'),
]

STAFF_LISTS = [
    ('positions',   'Employee Positions', 'positions'),
    ('departments', 'Departments',        'departments'),
    ('branches',    'Branches',           'branches'),
    ('banks',       'Banks',              'banks'),
]


def seed_forward(apps, schema_editor):
    JsonDataset = apps.get_model('core', 'JsonDataset')
    Setting = apps.get_model('core', 'Setting')

    try:
        ds1 = JsonDataset.objects.get(pk=1).dataset
    except JsonDataset.DoesNotExist:
        ds1 = {}

    for key, label, json_key in PRODUCT_LISTS:
        Setting.objects.get_or_create(
            key=key,
            defaults=dict(label=label, category='Products', value_type='list',
                          list_value=ds1.get(json_key, [])),
        )

    for key, label, json_key in STAFF_LISTS:
        Setting.objects.get_or_create(
            key=key,
            defaults=dict(label=label, category='Staff', value_type='list',
                          list_value=ds1.get(json_key, [])),
        )

    try:
        ds2 = JsonDataset.objects.get(pk=2).dataset
    except JsonDataset.DoesNotExist:
        ds2 = {}

    raw_date = ds2.get('closing-stock-date', [])
    Setting.objects.get_or_create(
        key='closing_stock_date',
        defaults=dict(label='Closing Stock Date', category='Stock',
                      value_type='date', text_value=raw_date[0] if raw_date else ''),
    )

    raw_gratuity = ds2.get('gratuity-title', [])
    Setting.objects.get_or_create(
        key='gratuity_title',
        defaults=dict(label='Gratuity Title', category='Staff',
                      value_type='text', text_value=raw_gratuity[0] if raw_gratuity else ''),
    )

    Setting.objects.get_or_create(
        key='balance_tolerance',
        defaults=dict(label='Balance Sheet Tolerance (NGN)', category='Trade',
                      value_type='number', text_value='1'),
    )


def seed_backward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    Setting.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_setting_model'),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_backward),
    ]
