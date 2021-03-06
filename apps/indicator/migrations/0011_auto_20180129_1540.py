# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-01-29 15:40
from __future__ import unicode_literals

from django.db import migrations, models
import unixtimestampfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('indicator', '0010_auto_20171212_0252'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventsElementary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.SmallIntegerField(choices=[(0, 'poloniex'), (1, 'bittrex')])),
                ('counter_currency', models.SmallIntegerField(choices=[(0, 'BTC'), (1, 'ETH'), (2, 'USDT'), (3, 'XMR')], default=0)),
                ('transaction_currency', models.CharField(max_length=6)),
                ('timestamp', unixtimestampfield.fields.UnixTimeStampField()),
                ('resample_period', models.PositiveSmallIntegerField(default=60)),
                ('event_name', models.CharField(default='none', max_length=32)),
                ('event_value', models.IntegerField(null=True)),
                ('event_second_value', models.FloatField(null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EventsLogical',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.SmallIntegerField(choices=[(0, 'poloniex'), (1, 'bittrex')])),
                ('counter_currency', models.SmallIntegerField(choices=[(0, 'BTC'), (1, 'ETH'), (2, 'USDT'), (3, 'XMR')], default=0)),
                ('transaction_currency', models.CharField(max_length=6)),
                ('timestamp', unixtimestampfield.fields.UnixTimeStampField()),
                ('resample_period', models.PositiveSmallIntegerField(default=60)),
                ('event_name', models.CharField(default='none', max_length=32)),
                ('event_value', models.IntegerField(null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PriceResampl',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.SmallIntegerField(choices=[(0, 'poloniex'), (1, 'bittrex')])),
                ('counter_currency', models.SmallIntegerField(choices=[(0, 'BTC'), (1, 'ETH'), (2, 'USDT'), (3, 'XMR')], default=0)),
                ('transaction_currency', models.CharField(max_length=6)),
                ('timestamp', unixtimestampfield.fields.UnixTimeStampField()),
                ('resample_period', models.PositiveSmallIntegerField(default=60)),
                ('open_price', models.BigIntegerField(null=True)),
                ('close_price', models.BigIntegerField(null=True)),
                ('low_price', models.BigIntegerField(null=True)),
                ('high_price', models.BigIntegerField(null=True)),
                ('midpoint_price', models.BigIntegerField(null=True)),
                ('mean_price', models.BigIntegerField(null=True)),
                ('price_variance', models.FloatField(null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Rsi',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.SmallIntegerField(choices=[(0, 'poloniex'), (1, 'bittrex')])),
                ('counter_currency', models.SmallIntegerField(choices=[(0, 'BTC'), (1, 'ETH'), (2, 'USDT'), (3, 'XMR')], default=0)),
                ('transaction_currency', models.CharField(max_length=6)),
                ('timestamp', unixtimestampfield.fields.UnixTimeStampField()),
                ('resample_period', models.PositiveSmallIntegerField(default=60)),
                ('relative_strength', models.FloatField(null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Sma',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.SmallIntegerField(choices=[(0, 'poloniex'), (1, 'bittrex')])),
                ('counter_currency', models.SmallIntegerField(choices=[(0, 'BTC'), (1, 'ETH'), (2, 'USDT'), (3, 'XMR')], default=0)),
                ('transaction_currency', models.CharField(max_length=6)),
                ('timestamp', unixtimestampfield.fields.UnixTimeStampField()),
                ('resample_period', models.PositiveSmallIntegerField(default=60)),
                ('sma_period', models.PositiveSmallIntegerField(default=50)),
                ('sma_high_price', models.BigIntegerField(null=True)),
                ('sma_close_price', models.BigIntegerField(null=True)),
                ('sma_midpoint_price', models.BigIntegerField(null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='priceresampled',
            name='resample_period',
            field=models.PositiveSmallIntegerField(default=60),
        ),
        migrations.AlterField(
            model_name='priceresampled',
            name='period',
            field=models.PositiveSmallIntegerField(default=60),
        ),
    ]
