from settings import LOAD_TALIB
if LOAD_TALIB:
    import talib

from apps.TA import HORIZONS
from apps.TA.storages.abstract.indicator import IndicatorStorage, BULLISH
from apps.TA.storages.abstract.indicator_subscriber import IndicatorSubscriber
from apps.TA.storages.data.price import PriceStorage
from settings import logger


class BbandsStorage(IndicatorStorage):

    def produce_signal(self):

        squeeze = self.upperband - self.lowerband
        if squeeze < 5:
            self.send_signal(trend=BULLISH, squeeze=squeeze)



class BbandsSubscriber(IndicatorSubscriber):

    classes_subscribing_to = [
        PriceStorage
    ]

    def handle(self, channel, data, *args, **kwargs):

        new_bband_storage = BbandsStorage(ticker=self.ticker,
                                     exchange=self.exchange,
                                     timestamp=self.timestamp)

        for horizon in HORIZONS:

            results_dict = PriceStorage.query(
                ticker=self.ticker,
                exchange=self.exchange,
                index=self.index,
                periods_range=horizon*5
            )

            value_np_array = self.get_values_array_from_query(results_dict, limit=horizon)

            upperband, middleband, lowerband = talib.BBANDS(
                value_np_array,
                timeperiod=len(value_np_array),
                nbdevup=2, nbdevdn=2, matype=0)

            logger.debug(f'saving RSI value {rsi_value} for {ticker} on {periods} periods')

            new_bband_storage.periods = horizon
            new_bband_storage.upperband = upperband
            new_bband_storage.middleband = middleband
            new_bband_storage.lowerband = lowerband
            new_bband_storage.value = ":".join(
                [int(value) for value in [upperband, middleband, lowerband]]
            )
            new_bband_storage.save()
