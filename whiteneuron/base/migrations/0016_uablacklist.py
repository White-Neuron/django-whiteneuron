import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0015_ipblacklist'),
    ]

    operations = [
        migrations.CreateModel(
            name='UABlacklist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pattern', models.CharField(
                    help_text='Substring or regex to match against the User-Agent header. E.g. \u2018GPTBot\u2019, \u2018https://openai.com\u2019.',
                    max_length=500,
                    unique=True,
                    verbose_name='pattern',
                )),
                ('is_regex', models.BooleanField(
                    default=False,
                    help_text='If checked, pattern is treated as a Python regex (re.search, case-insensitive); otherwise simple case-insensitive substring match.',
                    verbose_name='is regex',
                )),
                ('reason', models.CharField(blank=True, max_length=500, verbose_name='reason')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ua_blacklists',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='created by',
                )),
            ],
            options={
                'verbose_name': 'UA blacklist',
                'verbose_name_plural': 'UA blacklists',
                'db_table': 'ua_blacklists',
                'ordering': ['-created_at'],
            },
        ),
    ]
