import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0001_initial'),
        ('users', '0007_userinvite'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userinvite',
            name='email',
        ),
        migrations.AddField(
            model_name='userinvite',
            name='employee',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='user_invites',
                to='staff.employee',
                default=None,
            ),
            preserve_default=False,
        ),
    ]
