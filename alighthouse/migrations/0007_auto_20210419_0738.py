# Generated by Django 3.1.7 on 2021-04-19 02:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alighthouse', '0006_auto_20210418_1950'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lighthousereportbootupitems',
            name='url',
            field=models.CharField(max_length=65533),
        ),
        migrations.AlterField(
            model_name='lighthousereportlongtaskitem',
            name='url',
            field=models.CharField(max_length=65533),
        ),
        migrations.AlterField(
            model_name='lighthousereportnetworkreqitems',
            name='url',
            field=models.CharField(max_length=65533),
        ),
        migrations.AlterField(
            model_name='lighthousereportoffscreenimagesitem',
            name='url',
            field=models.CharField(max_length=65533),
        ),
        migrations.AlterField(
            model_name='lighthousereportunminifiedcss',
            name='url',
            field=models.CharField(max_length=65533, null=True),
        ),
        migrations.AlterField(
            model_name='lighthousereportunminifiedjs',
            name='url',
            field=models.CharField(max_length=65533, null=True),
        ),
        migrations.AlterField(
            model_name='lighthousereportunusedcssrule',
            name='url',
            field=models.CharField(max_length=65533, null=True),
        ),
    ]
