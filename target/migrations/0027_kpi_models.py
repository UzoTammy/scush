import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('target', '0026_remove_salestarget_achieved'),
    ]

    operations = [
        migrations.CreateModel(
            name='KPIBudget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metric', models.CharField(max_length=20, choices=[
                    ('gross_profit', 'Gross Profit'),
                    ('direct_expense', 'Direct Expenses'),
                    ('indirect_expense', 'Indirect Expenses'),
                    ('margin_pct', 'Margin %'),
                    ('growth_pct', 'Growth %'),
                ])),
                ('annual_value', models.DecimalField(max_digits=16, decimal_places=2)),
                ('budget_year', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='kpi_budgets',
                    to='target.budgetyear',
                )),
            ],
            options={'verbose_name': 'KPI Annual Budget', 'ordering': ['metric']},
        ),
        migrations.AlterUniqueTogether(
            name='kpibudget',
            unique_together={('budget_year', 'metric')},
        ),
        migrations.CreateModel(
            name='KPIMonthlyTarget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.PositiveSmallIntegerField(choices=[
                    (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
                    (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
                    (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
                ])),
                ('metric', models.CharField(max_length=20, choices=[
                    ('gross_profit', 'Gross Profit'),
                    ('direct_expense', 'Direct Expenses'),
                    ('indirect_expense', 'Indirect Expenses'),
                    ('margin_pct', 'Margin %'),
                    ('growth_pct', 'Growth %'),
                ])),
                ('target_value', models.DecimalField(max_digits=16, decimal_places=2)),
                ('budget_year', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='kpi_monthly_targets',
                    to='target.budgetyear',
                )),
            ],
            options={'verbose_name': 'KPI Monthly Target', 'ordering': ['budget_year__year', 'month', 'metric']},
        ),
        migrations.AlterUniqueTogether(
            name='kpimonthlytarget',
            unique_together={('budget_year', 'month', 'metric')},
        ),
    ]
