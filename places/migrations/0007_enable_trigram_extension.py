# Generated migration to enable PostgreSQL trigram extension for fuzzy search

from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('places', '0006_search_improvements'),
    ]

    operations = [
        TrigramExtension(),
    ]
