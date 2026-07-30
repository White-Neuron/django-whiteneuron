# Generated migration - manual

from django.db import migrations, models
import django.db.models.deletion


def create_templates_from_existing_mails(apps, schema_editor):
    """Create EmailTemplate entries from existing Mail records, grouping by identical subject+content."""
    Mail = apps.get_model('base', 'Mail')
    EmailTemplate = apps.get_model('base', 'EmailTemplate')
    
    # Get all unique (subject, content) combinations
    seen = {}  # key -> template_id
    
    for mail in Mail.objects.all():
        key = f"{mail.subject}|||{mail.content}"[:500]
        if key not in seen:
            template = EmailTemplate.objects.create(
                name=f"Template ({key[:20]}...)",
                subject=mail.subject,
                content=mail.content,
            )
            seen[key] = template.id
        
        # Update mail to reference the template
        Mail.objects.filter(id=mail.id).update(template_id=seen[key])


def reverse_create_mails(apps, schema_editor):
    """Reverse: copy template data back to mail records (for safety)."""
    Mail = apps.get_model('base', 'Mail')
    
    for mail in Mail.objects.all():
        if mail.template_id:
            Mail.objects.filter(id=mail.id).update(
                subject=mail.template.subject,
                content=mail.template.content,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0027_alter_anonymousactivity_method_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('is_deleted', models.BooleanField(default=False, verbose_name='Deleted')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted at')),
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='Date created')),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='Date updated')),
                ('is_hidden', models.BooleanField(default=False, verbose_name='Hidden')),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('subject', models.TextField(verbose_name='Subject')),
                ('content', models.TextField(verbose_name='Content')),
                ('created_by', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to='base.user', verbose_name='Created by')),
                ('updated_by', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to='base.user', verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Email template',
                'verbose_name_plural': 'Email templates',
                'db_table': 'email_template',
            },
        ),
        migrations.AddField(
            model_name='mail',
            name='template',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='base.emailtemplate', verbose_name='Template'),
        ),
        migrations.RunPython(create_templates_from_existing_mails, reverse_create_mails),
        migrations.AlterField(
            model_name='mail',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.emailtemplate', verbose_name='Template'),
        ),
    ]
