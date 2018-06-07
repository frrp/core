import time
import logging
import json

from requests import get

from apps.channel.models import ExchangeData
from apps.indicator.models import Price, Volume
from apps.indicator.models.price import get_currency_value_from_string


logger = logging.getLogger(__name__)


def _pull_poloniex_data(source):
    logger.info("pulling Poloniex data...")
    req = get('https://poloniex.com/public?command=returnTicker')

    data = req.json()
    timestamp = time.time()

    ExchangeData.objects.create(
        source=source,
        data=json.dumps(data),
        timestamp=timestamp
    )
    logger.info("Saving Poloniex price, volume data...")
    _save_prices_and_volumes(data, timestamp, source)


def _save_prices_and_volumes(data, timestamp, source):
    for currency_pair in data:
        try:
            counter_currency_string = currency_pair.split('_')[0]
            counter_currency = get_currency_value_from_string(counter_currency_string)
            # assert counter_currency >= 0
            transaction_currency_string = currency_pair.split('_')[1]
            # assert len(transaction_currency_string) > 1 and len(transaction_currency_string) <= 6

            Price.objects.create(
                source=source,
                transaction_currency=transaction_currency_string,
                counter_currency=counter_currency,
                price=int(float(data[currency_pair]['last']) * 10 ** 8),
                timestamp=timestamp
            )

            Volume.objects.create(
                source=source,
                transaction_currency=transaction_currency_string,
                counter_currency=counter_currency,
                volume=float(data[currency_pair]['baseVolume']),
                timestamp=timestamp
            )
        except Exception as e:
            logger.debug(str(e))

    logger.debug("Saved Poloniex price and volume data")


# def _compute_and_save_indicators(source, resample_period):#params):
#     #source = params['source']
#     #resample_period = params['period']

#     horizon = get_horizon_value_from_string(display_string=HORIZONS_TIME2NAMES[resample_period])

#     timestamp = time.time() // (1 * 60) * (1 * 60)   # rounded to a minute

#     logger.info("################# Resampling with Period: " + str(resample_period) + ", Source:" + str(source) + " #######################")

#     # Uncomment  to test backtesting
#     #strategies_list = add_all_strategies()
#     #_backtest_all_strategies()

#     if RUN_ANN:
#         # choose the pre-trained ANN model depending on period, here are the same
#         period2model = {
#             SHORT : 'lstm_model_2_2.h5',
#             MEDIUM: 'lstm_model_2_2.h5',
#             LONG  : 'lstm_model_2_2.h5'
#         }
#         # load model from S3 and database
#         ann_model_object = get_ann_model_object(period2model[resample_period])

#     #TODO: get pairs from def(SOURCE)
#     #pairs_to_iterate = [(itm,Price.USDT) for itm in USDT_COINS] + [(itm,Price.BTC) for itm in BTC_COINS]

#     pairs_to_iterate = get_currency_pairs(source=source, period_in_seconds=resample_period*60*2)
#     #logger.debug("## Pairs to iterate: " + str(pairs_to_iterate))

#     for transaction_currency, counter_currency in pairs_to_iterate:
#         logger.info('   ======== EXCHANGE: ' + str(source) + '| period: ' + str(resample_period)+ '| checking COIN: ' + str(transaction_currency) + ' with BASE_COIN: ' + str(counter_currency))

#         # create a dictionary of parameters to improve readability
#         indicator_params_dict = {
#             'timestamp': timestamp,
#             'source': source,
#             'transaction_currency': transaction_currency,
#             'counter_currency': counter_currency,
#             'resample_period': resample_period
#         }


#         ################# BACK CALCULATION (need only once when run first time)
#         BACK_REC = 5   # how many records to calculate back in time
#         BACK_TIME = timestamp - BACK_REC * resample_period * 60  # same in sec

#         last_time_computed = get_first_resampled_time(source, transaction_currency, counter_currency, resample_period)
#         records_to_compute = int((last_time_computed-BACK_TIME)/(resample_period * 40))

#         if records_to_compute >= 0:
#             logger.info("  ... calculate resampl back in time, needed records: " + str(records_to_compute))
#             for idx in range(1, records_to_compute):
#                 time_point_back = last_time_computed - idx * (resample_period * 60)
#                 # round down to the closest hour
#                 indicator_params_dict['timestamp'] = time_point_back // (60 * 60) * (60 * 60)

#                 try:
#                     resample_object = PriceResampl.objects.create(**indicator_params_dict)
#                     status = resample_object.compute()
#                     if status or (idx == records_to_compute-1) : # leave the last empty record
#                         resample_object.save()
#                     else:
#                         resample_object.delete()  # delete record if no price was added
#                 except Exception as e:
#                     logger.error(" -> Back RESAMPLE EXCEPTION: " + str(e))

#             logger.debug("... resample back  - DONE.")
#         else:
#             logger.debug("   ... No back calculation needed")

#         # set time back to a current time
#         indicator_params_dict['timestamp'] = timestamp
#         ################# Can be commented after first time run


#         # 1 ############################
#         # calculate and save resampling price
#         # todo - prevent adding an empty record if no value was computed (static method below)
#         try:
#             resample_object = PriceResampl.objects.create(**indicator_params_dict)
#             resample_object.compute()
#             if MODIFY_DB: resample_object.save()  #we set MODIFY_DB = False for debug mode, so we can debug with real DB
#             logger.debug("  ... Resampled completed,  ELAPSED Time: " + str(time.time() - timestamp))
#         except Exception as e:
#             logger.error(" -> RESAMPLE EXCEPTION: " + str(e))


#         # 2 ###########################
#         # calculate and save simple indicators
#         indicators_list = [Sma, Rsi]
#         for ind in indicators_list:
#             try:
#                 ind.compute_all(ind, **indicator_params_dict)
#                 logger.debug("  ... Regular indicators completed,  ELAPSED Time: " + str(time.time() - timestamp))
#             except Exception as e:
#                 logger.error(str(ind) + " Indicator Exception: " + str(e))



#         # calculate ANN indicator(s)
#         # TODO: now run only for a short period, since it is not really tuned for other periods
#         if (RUN_ANN) and (resample_period==SHORT):
#             # TODO: just form X_predicted here and then run prediction outside the loop !
#             try:
#                 if ann_model_object:
#                     AnnPriceClassification.compute_all(AnnPriceClassification, ann_model_object, **indicator_params_dict)
#                     logger.info("  ... ANN indicators completed,  ELAPSED Time: " + str(time.time() - timestamp))
#                 else:
#                     logger.error(" No ANN model, calculation does not make sence")
#             except Exception as e:
#                 logger.error("ANN Indicator Exception (ANN has not been calculated): " + str(e))



#         # 4 #############################
#         # check for events and save if any
#         events_list = [EventsElementary, EventsLogical]
#         for event in events_list:
#             try:
#                 event.check_events(event, **indicator_params_dict)
#                 logger.debug("  ... Events completed,  ELAPSED Time: " + str(time.time() - timestamp))
#             except Exception as e:
#                 logger.error(" Event Exception: " + str(e))


#         # 5 ############################
#         # TODO: Uncomment when strategies are ready, it will emit strategy signals
#         # check if we have to emit any <Strategy> signals

#         strategies_list = get_all_strategy_classes()  # [RsiSimpleStrategy, SmaCrossOverStrategy]

#         for strategy in strategies_list:
#             try:
#                 s = strategy(**indicator_params_dict)
#                 now_signals_set = s.check_signals_now()
#                 logger.debug("  NOW: found Signal belongs to strategy : " + str(strategy) + " : " + str(now_signals_set))

#                 # Emit to a signal from a strategy to sqs without saving it in the Signal table
#                 # combine a dictionary with all data
#                 dict_to_emit = {
#                     **indicator_params_dict,
#                     "horizon"  : horizon,
#                     "strategy" : str(s),
#                     "signal_name" : str(now_signals_set)
#                 }
#                 send_sqs(dict_to_emit)
#                 logger.debug("   ... Checking for strategy signals completed.")
#             except Exception as e:
#                 logger.error(" Error Strategy checking:  " + str(e))


#     # clean session to prevent memory leak
#     if RUN_ANN:
#         # clean session to prevent memory leak
#         logger.debug("   ... Cleaning Keras session...")
#         from keras import backend as K
#         K.clear_session()
