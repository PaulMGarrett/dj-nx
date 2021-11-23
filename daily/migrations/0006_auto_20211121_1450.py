# Generated by Django 3.2.8 on 2021-11-21 14:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('daily', '0005_exercise_oedema_weight'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='exercise',
            name='id',
        ),
        migrations.RemoveField(
            model_name='oedema',
            name='id',
        ),
        migrations.RemoveField(
            model_name='weight',
            name='id',
        ),
        migrations.AlterField(
            model_name='exercise',
            name='date0',
            field=models.DateField(primary_key=True, serialize=False, verbose_name='date'),
        ),
        migrations.AlterField(
            model_name='oedema',
            name='date0',
            field=models.DateField(primary_key=True, serialize=False, verbose_name='date'),
        ),
        migrations.AlterField(
            model_name='weight',
            name='date0',
            field=models.DateField(primary_key=True, serialize=False, verbose_name='date measured'),
        ),
    ]
