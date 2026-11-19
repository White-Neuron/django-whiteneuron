from django.db import migrations, models


def status_from_is_resolved(apps, schema_editor):
    FeedbackData = apps.get_model("feedbacks", "FeedbackData")
    FeedbackData.objects.filter(is_resolved=True).update(status="resolved")


class Migration(migrations.Migration):

    dependencies = [
        ('feedbacks', '0007_created_by_updated_by_set_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedbackdata',
            name='status',
            # db_default too: during a rolling deploy the previous release still inserts rows
            # without this column
            field=models.CharField(choices=[('open', 'Open'), ('in_progress', 'In progress'), ('resolved', 'Resolved'), ('rejected', 'Rejected')], db_default='open', db_index=True, default='open', max_length=20, verbose_name='Status'),
        ),
        migrations.RunPython(status_from_is_resolved, migrations.RunPython.noop),
        # help texts that only repeated the labels ("The message of the feedback", #81 / #103)
        migrations.AlterField(
            model_name='feedbackdata',
            name='is_resolved',
            field=models.BooleanField(default=False, verbose_name='Is Resolved'),
        ),
        migrations.AlterField(
            model_name='feedbackdata',
            name='message',
            field=models.TextField(verbose_name='Message'),
        ),
        migrations.AlterField(
            model_name='feedbackdata',
            name='note',
            field=models.TextField(blank=True, null=True, verbose_name='Note'),
        ),
    ]
