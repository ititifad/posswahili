# Generated by Django 5.1 on 2024-09-05 09:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_saleitem_refund_reason_saleitem_refunded_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='saleitem',
            name='is_fully_refunded',
            field=models.BooleanField(default=False),
        ),
    ]
