import logging
import time
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from apps.TA.storages.abstract.timeseries_storage import TimeseriesStorage
from apps.common.utilities.multithreading import start_new_thread, multithread_this_shit
from settings.redis_db import database
from apps.indicator.models.price_history import PriceHistory
from apps.TA.storages.data.pv_history import PriceVolumeHistoryStorage, default_price_indexes, default_volume_indexes

logger = logging.getLogger(__name__)

try:
    earliest_price_timestamp = int(float(
        database.zrangebyscore("BTC:bittrex:PriceStorage:close_price", 0, "inf", 0, 1)[0].decode("utf-8").split(":")[
            0]))
except:
    earliest_price_timestamp = int(time.time())


class Command(BaseCommand):
    help = 'Run Redis Subscribers for TA'

    def handle(self, *args, **options):
        logger.info("Starting TA restore script.")

        today = datetime.now()
        start_day = datetime(today.year, today.month, today.day)

        start_day = datetime(2018, 1, 1)
        end_day = datetime(2018, 8, 29)
        assert start_day < end_day  # please go forward in time :)
        process_day = start_day


        while process_day < end_day:
            process_day += timedelta(days=1)
            price_history_objects = PriceHistory.objects.filter(
                timestamp__gte=process_day - timedelta(days=1),
                timestamp__lt=process_day
            )

            results = multithread_this_shit(save_pv_histories_to_redis, price_history_objects)
            total_results = sum([sum(result) for result in results])

            # for ph_object in price_history_objects:
            #     if ph_object.transaction_currency not in transaction_currencies:
            #         continue
            #     pipeline = save_pv_histories_to_redis(ph_object)
            # database_response = pipeline.execute()
            # total_results = sum(database_response)

            logger.debug(f"{sum(total_results)} values added to Redis")

            price_history_to_price_storage(
                ticker_exchanges=[(pho.ticker, pho.exchange) for pho in price_history_objects],
                start_score=TimeseriesStorage.score_from_timestamp((process_day - timedelta(days=1)).timestamp()),
                end_score=TimeseriesStorage.score_from_timestamp(process_day.timestamp())
            )


### PULL PRICE HISTORY RECORDS FROM CORE PRICE HISTORY DATABASE ###
def save_pv_histories_to_redis(ph_object, pipeline=None):

    if ph_object.transaction_currency not in transaction_currencies:
        return pipeline or [0]

    using_local_pipeline = (not pipeline)

    if using_local_pipeline:
        pipeline = database.pipeline()  # transaction=False

    ticker = f'{ph_object.transaction_currency}_{ph_object.get_counter_currency_display()}'
    exchange = str(ph_object.get_source_display())
    unix_timestamp = int(ph_object.timestamp.timestamp())


    # SAVE VALUES IN REDIS USING PriceVolumeHistoryStorage OBJECT
    # CREATE OBJECT FOR STORAGE
    pv_storage = PriceVolumeHistoryStorage(
        ticker=ticker,
        exchange=exchange,
        timestamp=unix_timestamp
    )

    if ph_object.volume and ph_object.volume > 0:
        pv_storage.index = "close_volume"
        pv_storage.value = ph_object.volume
        pipeline = pv_storage.save(publish=False, pipeline=pipeline)

    if ph_object.open_p and ph_object.open_p > 0:
        pv_storage.index = "open_price"
        pv_storage.value = ph_object.open_p
        pipeline = pv_storage.save(publish=True, pipeline=pipeline)

    if ph_object.high and ph_object.high > 0:
        pv_storage.index = "high_price"
        pv_storage.value = ph_object.high
        pipeline = pv_storage.save(publish=True, pipeline=pipeline)

    if ph_object.low and ph_object.low > 0:
        pv_storage.index = "low_price"
        pv_storage.value = ph_object.low
        pipeline = pv_storage.save(publish=True, pipeline=pipeline)

    # always run 'close_price' index last
    # why? when it saves, it triggers price storage to resample
    # after resampling history indexes are deleted
    # so all others should be available for resampling before being deleted

    if ph_object.close and ph_object.close > 0:
        pv_storage.index = "close_price"
        pv_storage.value = ph_object.close
        pipeline = pv_storage.save(publish=True, pipeline=pipeline)

    if using_local_pipeline:
        return pipeline.execute()
    else:
        return pipeline

### END PULL OF PRICE HISTORY RECORDS ###


### RESAMPLE PRICES TO 5 MIN PRICE STORAGE RECORDS ###
@start_new_thread
def price_history_to_price_storage(ticker_exchanges, start_score=None, end_score=None):
    from apps.TA.storages.utils.pv_resampling import generate_pv_storages

    if not start_score:
        # start_score = 0  # this is jan 1 2017
        start_score = int((datetime(2018,9,1).timestamp() - datetime(2017,1,1).timestamp())/300)  # this is Sep 1 2018
    processing_score = start_score

    if not end_score:
        end_score = TimeseriesStorage.score_from_timestamp((datetime.today() - timedelta(hours=2)).timestamp())

    while processing_score < end_score:
        processing_score += 1

        for ticker, exchange in ticker_exchanges:

            for index in default_price_indexes:
                if generate_pv_storages(ticker, exchange, index, processing_score):
                    if index == "close_price":
                        from apps.TA.storages.utils.memory_cleaner import clear_pv_history_values
                        clear_pv_history_values(ticker, exchange, processing_score)

    # returns nothing - can be threaded with collection of results
### END RESAMPLE FOR PRICE STORAGE RECORDS ###


transaction_currencies = [
    'XVG', 'IOTX', 'LTC', 'YOYOW', 'STR', 'TRX', 'ADA', 'CDT', 'VET', 'KEY', 'HOT', 'AGI', 'XMR', 'LEND', 'DENT',
    'NPXS', 'ZIL', 'XRP', 'IOST', 'EOS', 'VRC', 'ETH', 'ETC', 'NCASH', 'AST', 'RPX', 'VIB', 'ZRX', 'DGB', 'BTC', 'SC',
    'MFT', 'GTO', 'XEM', 'DASH', 'DOGE', 'XLM', 'FCT', 'BAT', 'QKC', 'POE', 'ENJ', 'FUN', 'STRAT', 'ICX', 'BCN', 'TNB',
    'CHAT', 'DOCK', 'REQ', 'IOTA', 'STORM', 'TNT', 'SNT', 'FUEL', 'BCH', 'LSK', 'OMG', 'BTS', 'WPR', 'ZEC', 'GAME',
    'MTH', 'OST', 'RCN', 'REP'
]
counter_currencies = [
    'BTC', 'ETH', 'USDT'
]