from django.db import models
from settings import HORIZONS_TIME2NAMES, LONG, MODIFY_DB

from apps.indicator.models.abstract_indicator import AbstractIndicator
from apps.signal.models.signal import Signal
from apps.indicator.models.events_elementary import get_current_elementory_events_df, get_last_ever_entered_elementory_events_df
from apps.indicator.models.rsi import Rsi
from apps.user.models.user import get_horizon_value_from_string

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EventsLogical(AbstractIndicator):
    event_name = models.CharField(max_length=32, null=False, blank=False, default="none")
    event_value = models.IntegerField(null=True)

    @staticmethod
    def check_events(cls, **kwargs):
        resample_period = kwargs['resample_period']
        horizon = get_horizon_value_from_string(display_string=HORIZONS_TIME2NAMES[resample_period])

        logger.info('   ::::  Start analysing LOGICAL events ::::')
        # get all elementory events
        # always one line!
        last_events_df = get_current_elementory_events_df(**kwargs)

        if not last_events_df.empty:
            ###################### Ichi kumo breakout UP
            logger.debug("   ... Check Ichimoku Breakout UP Event ")

            last_events_df['kumo_breakout_up_signal'] = np.where(
                (last_events_df.close_cloud_breakout_up_ext &
                 last_events_df.lagging_above_cloud &
                 last_events_df.lagging_above_highest &
                 last_events_df.conversion_above_base
                 ) == True,
                1, 0)

            # save logical event and emit signal - we need all because it is s Series
            if all(last_events_df['kumo_breakout_up_signal']):

                try:
                    kumo_event_up = cls(
                        **kwargs,
                        event_name='kumo_breakout_up_signal',
                        event_value=int(1),
                    )
                    if MODIFY_DB: kumo_event_up.save()   # do not modify DB in debug mode

                    signal_kumo_up = Signal(
                        **kwargs,
                        signal='kumo_breakout',
                        trend = int(1),  # positive trend means it is UP / bullish signal
                        strength_value=int(3),
                        horizon=horizon,
                    )
                    if MODIFY_DB: signal_kumo_up.save()
                    logger.info('  >>> YOH! Kumo breakout UP has been FIRED!')
                except Exception as e:
                    logger.error(" Error saving kumo_breakout_up_signal ")
            else:
                logger.debug("   .. No kumo_breakout_up_signals")


            ######################## Ichi kumo breakout DOWN
            logger.debug("   ... Check Ichimoku Breakout DOWN Event ")

            last_events_df['kumo_breakout_down_signal'] = np.where(
                (last_events_df.close_cloud_breakout_down_ext &
                 last_events_df.lagging_below_cloud &
                 last_events_df.lagging_below_cloud &
                 last_events_df.conversion_below_base
                 ) == True,
                1, 0)

            # save logical event and emit signal
            if all(last_events_df['kumo_breakout_down_signal']):

                try:
                    kumo_event_down = cls(
                        **kwargs,
                        event_name='kumo_breakout_down_signal',
                        event_value=int(1),
                    )
                    if MODIFY_DB: kumo_event_down.save()

                    signal_kumo_down = Signal(
                        **kwargs,
                        signal='kumo_breakout',
                        trend=int(-1),  # negative is bearish
                        strength_value=int(3),
                        horizon=horizon,
                    )
                    if MODIFY_DB: signal_kumo_down.save()
                    logger.info('   >>> YOH! Kumo breakout DOWN has been FIRED!')
                except Exception as e:
                    logger.error(" Error saving kumo_breakout_down_signal ")

            else:
                logger.debug("   .. No kumo_breakout_down events.")

            # DEBUG: print all events if any
            for name, values in last_events_df.iteritems():
                if values[0]:
                    logger.debug('    ... event: ' + name + ' = ' + str(values[0]) )


            ############# check for ITT Cummulative RSI Signal
            logger.debug("   ... Check RSI Cumulative Event ")

            # get events for long time period (not for current)
            long_param_dict = kwargs.copy()
            long_param_dict['resample_period'] = LONG
            long_period_events_df = get_last_ever_entered_elementory_events_df(**long_param_dict)

            # get last rsi object for current period
            rs_obj = Rsi.objects.filter(**kwargs).last()

            # add a long period signal to the current signals
            if not long_period_events_df.empty:
                #logger.debug("      @nice! long period events:  " + str(long_period_events_df))
                last_events_df['long_sma50_above_sma200'] = int(long_period_events_df['sma50_above_sma200'])
                last_events_df['long_sma50_below_sma200'] = int(long_period_events_df['sma50_below_sma200'])

                # detect
                #logger.debug("      - before RSI_Cumulative_bullish")
                last_events_df['RSI_Cumulative_bullish'] = np.where(
                (
                    last_events_df['long_sma50_above_sma200'] &
                    ( last_events_df['rsi_bracket']).isin([-2,-3] )
                 ) == True,
                1, 0)

                last_events_df['RSI_Cumulative_bearish'] = np.where(
                (
                    last_events_df['long_sma50_below_sma200'] &
                    (last_events_df['rsi_bracket'].isin([2,3]) )
                 ) == True,
                1, 0)

                # save and emit signals if neccesary
                logger.debug("      - saving ... ")
                if all(last_events_df['RSI_Cumulative_bullish']):
                    logger.info('    YOH! RSI_Cumulative_bullish has been DETECTED!')
                    try:
                        rsi_cum_up = cls(
                            **kwargs,
                            event_name='RSI_Cumulative_bullish',
                            event_value= rs_obj.rsi
                            #np.sign(last_events_df['rsi_bracket'].tail(1).values[0]),
                        )
                        if MODIFY_DB: rsi_cum_up.save()

                        signal_rsi_cum_up = Signal(
                            **kwargs,
                            signal='RSI_Cumulative',
                            rsi_value=rs_obj.rsi,
                            trend=np.sign(last_events_df['rsi_bracket'].tail(1).values[0]),
                            #strength_value=int(3),
                            horizon=horizon,
                            strength_value=np.abs(last_events_df['rsi_bracket'].tail(1).values[0]),
                            strength_max=int(3),
                        )
                        if MODIFY_DB: signal_rsi_cum_up.save()
                        logger.info('    RSI_Cumulative_bullish has been Saved!')
                    except Exception as e:
                        logger.error(" Error saving RSI_Cumulative_bullish signal ")
                logger.debug("    ... No RSI_Cumulative_bullish event")


                if all(last_events_df['RSI_Cumulative_bearish']):
                    logger.info('    YOH! RSI_Cumulative_bearish has been DETECTED!')
                    try:
                        rsi_cum_down = cls(
                            **kwargs,
                            event_name='RSI_Cumulative_bearish',
                            event_value= rs_obj.rsi
                            #np.sign(last_events_df['rsi_bracket'].tail(1).values[0]),
                        )
                        if MODIFY_DB: rsi_cum_down.save()

                        signal_rsi_cum_down = Signal(
                            **kwargs,
                            signal='RSI_Cumulative',
                            rsi_value=rs_obj.rsi,
                            trend=np.sign(last_events_df['rsi_bracket'].tail(1).values[0]),
                            #strength_value=int(3),
                            horizon=horizon,
                            strength_value=np.abs(last_events_df['rsi_bracket'].tail(1).values[0]),
                            strength_max=int(3),
                        )
                        if MODIFY_DB: signal_rsi_cum_down.save()
                        logger.info('    RSI_Cumulative_bearish has been Saved!')
                    except Exception as e:
                        logger.error(" Error saving RSI_Cumulative_bearish signal ")
                logger.debug("    ... No RSI_Cumulative_bearish event")

            else:
                logger.debug("   .. no long term data yet ... so, no RSI Cumulative.")


            ####################### Ben Events #####################
            logger.debug("   ... Check Ben Event ")

            last_events_df['ben_volume_based_buy'] = np.where(
                ((last_events_df.vbi_price_gt_mean_by_percent &
                  last_events_df.vbi_volume_cross_from_below) |
                 (last_events_df.vbi_volume_gt_mean_by_percent &
                  last_events_df.vbi_price_cross_from_below)
                 ) == True,
                1, 0)


            #last_events_df['ben_volume_based_buy'] = np.where(
            #    (last_events_df.close_cloud_breakout_down_ext &
            #     last_events_df.lagging_below_cloud &
            #     last_events_df.lagging_below_cloud &
            #     last_events_df.conversion_below_base
            #     ) == True,
            #    1, 0)

            # save logical event and emit signal
            if all(last_events_df['ben_volume_based_buy']):

                try:
                    ben_buy = cls(
                        **kwargs,
                        event_name='ben_volume_based_buy',
                        event_value=int(1),
                    )
                    if MODIFY_DB: ben_buy.save()

                    signal_ben_buy = Signal(
                        **kwargs,
                        signal='VBI',
                        trend=int(1),
                        strength_value=int(3),
                        horizon=horizon,
                    )
                    if MODIFY_DB: signal_ben_buy.save()
                    logger.info('   >>> Ben UP signal has been FIRED!')
                except Exception as e:
                    logger.error(" Error saving Ben UP signal ")

            else:
                logger.debug("   .. No ben Up  events.")

        else:
            logger.debug("   ... No elementary events found at all, skip processing !")
            return pd.DataFrame()

