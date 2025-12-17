# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='document_key',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
