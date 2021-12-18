# Generated by Django 3.2.8 on 2021-12-09 21:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nx', '0003_auto_20211209_2101'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tirednesslevel',
            name='score',
        ),
        migrations.AddField(
            model_name='tirednesslevel',
            name='rating',
            field=models.IntegerField(default=1, verbose_name='tiredness level'),
            preserve_default=False,
        ),
    ]
