# Generated by Django 3.2.8 on 2021-12-09 21:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('nx', '0002_auto_20211123_1523'),
    ]

    operations = [
        migrations.CreateModel(
            name='TirednessLevel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.FloatField(verbose_name='tiredness level')),
                ('description', models.CharField(max_length=30, verbose_name='description')),
            ],
        ),
        migrations.RemoveField(
            model_name='obs',
            name='fatigue_score',
        ),
        migrations.AddField(
            model_name='obs',
            name='tiredness',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='nx.tirednesslevel'),
        ),
    ]
