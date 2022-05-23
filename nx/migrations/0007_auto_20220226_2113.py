# Generated by Django 3.2.8 on 2022-02-26 21:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nx', '0006_auto_20220109_1044'),
    ]

    operations = [
        migrations.AddField(
            model_name='obs',
            name='am_rate',
            field=models.IntegerField(blank=True, null=True, verbose_name='Morning resting heart rate'),
        ),
        migrations.AddField(
            model_name='obs',
            name='other_rate',
            field=models.IntegerField(blank=True, null=True, verbose_name='Extra resting heart rate'),
        ),
        migrations.AddField(
            model_name='obs',
            name='pm_rate',
            field=models.IntegerField(blank=True, null=True, verbose_name='Afternoon resting heart rate'),
        ),
    ]
