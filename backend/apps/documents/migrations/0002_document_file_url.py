# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='file_url',
            field=models.URLField(blank=True, max_length=1000),
        ),
    ]
