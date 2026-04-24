# Generated manually to safely add uuid to existing users

from django.db import migrations, models
import uuid


def add_uuid_to_existing_users(apps, schema_editor):
    User = apps.get_model('base', 'User')
    for user in User.objects.all():
        new_uuid = uuid.uuid4()
        User.objects.filter(pk=user.pk).update(uuid=new_uuid)


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0017_alter_uablacklist_pattern'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(add_uuid_to_existing_users, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
