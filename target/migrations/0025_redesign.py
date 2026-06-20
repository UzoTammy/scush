import datetime
import django.core.validators
import django.db.models.deletion
import djmoney.models.fields
from django.db import migrations, models
from djmoney.money import Money


class Migration(migrations.Migration):

    dependencies = [
        ('target', '0024_alter_sales_center_default'),
    ]

    operations = [
        # Drop whatever old tables exist (safe regardless of which prior version ran)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel('Sales'),
                migrations.DeleteModel('PositionKPIMonthly'),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'DROP TABLE IF EXISTS target_sales CASCADE;'
                        'DROP TABLE IF EXISTS target_positionkpimonthly CASCADE;'
                        'DROP TABLE IF EXISTS target_kpitarget CASCADE;'
                        'DROP TABLE IF EXISTS target_salestarget CASCADE;'
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # Create BudgetYear
        migrations.CreateModel(
            name='BudgetYear',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('year', models.PositiveSmallIntegerField(
                    unique=True,
                    default=datetime.date.today().year,
                    validators=[
                        django.core.validators.MinValueValidator(2020),
                        django.core.validators.MaxValueValidator(2040),
                    ],
                )),
                ('sales_budget_currency', djmoney.models.fields.CurrencyField(
                    choices=[('NGN', 'Nigerian Naira')], default='NGN',
                    editable=False, max_length=3)),
                ('sales_budget', djmoney.models.fields.MoneyField(
                    decimal_places=2, default_currency='NGN', max_digits=14)),
            ],
            options={
                'verbose_name': 'Budget Year',
                'ordering': ['-year'],
            },
        ),

        # Create SalesTarget
        migrations.CreateModel(
            name='SalesTarget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('budget_year', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='monthly_targets',
                    to='target.budgetyear',
                )),
                ('month', models.PositiveSmallIntegerField(
                    choices=[
                        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
                        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
                        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
                    ],
                )),
                ('target_currency', djmoney.models.fields.CurrencyField(
                    choices=[('NGN', 'Nigerian Naira')], default='NGN',
                    editable=False, max_length=3)),
                ('target', djmoney.models.fields.MoneyField(
                    decimal_places=2, default_currency='NGN', max_digits=14)),
                ('achieved_currency', djmoney.models.fields.CurrencyField(
                    choices=[('NGN', 'Nigerian Naira')], default='NGN',
                    editable=False, max_length=3)),
                ('achieved', djmoney.models.fields.MoneyField(
                    decimal_places=2, default_currency='NGN', max_digits=14,
                    default=Money(0, 'NGN'))),
            ],
            options={
                'verbose_name': 'Monthly Sales Target',
                'ordering': ['budget_year__year', 'month'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='salestarget',
            unique_together={('budget_year', 'month')},
        ),
    ]
