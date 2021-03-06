import logging
import textwrap
import time

from django.core.management.base import BaseCommand

from settings import POLONIEX, SHORT, MEDIUM, USDT
from settings import time_speed  # 1 / 10

from taskapp.helpers.poloniex import _pull_poloniex_data
from taskapp.helpers.indicators import _compute_indicators_for, _compute_ann
from taskapp.helpers.backtesting import _backtest_all_strategies
from taskapp.helpers.sentiment_analysis import _analyze_sentiment
from taskapp.helpers.common import get_currency_pairs



logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run: manage.py trawl_poloniex info (use only for local testing)"

    # Currently we use this command for debug only
    def add_arguments(self, parser):
        parser.add_argument('arg', nargs='?', default='compute_indicators_for_poloniex', type=str)

    def handle(self, *args, **options):
        arg = options['arg']

        if arg == 'pull_data':
            logger.info("This command was disabled. Please don't use it")
            # logger.info("Getting ready to trawl Poloniex...\n>>> Break it when you'll get enough samples <<<")
            # while True:
            #     _pull_poloniex_data()
            #     time.sleep(60/time_speed)

        elif arg == 'compute_pair':
            _compute_indicators_for(transaction_currency='BTC', counter_currency=USDT,
                                    source=POLONIEX, resample_period=SHORT)

        elif arg == 'compute_indicators':
            for (t_currency, c_currency) in get_currency_pairs(source=POLONIEX, period_in_seconds=1*60*60):
                _compute_indicators_for(source=POLONIEX, transaction_currency=t_currency,
                                        counter_currency=c_currency, resample_period=MEDIUM)  # SHORT
        elif arg == 'ann':
            from taskapp.tasks import compute_ann_for_all_sources
            #compute_ann_for_all_sources(resample_period=SHORT)
            #_compute_ann(source=POLONIEX, resample_period=SHORT)
            _compute_ann(source=POLONIEX, resample_period=MEDIUM)

        elif arg == 'backtest':
            _backtest_all_strategies()

        elif arg == 'sentiment':
            _analyze_sentiment()


        else:
            print(textwrap.dedent("""How to use:
            manage.py trawl_poloniex <arg>, where <arg>:
                * pull_data - download tickers from POLONIEX. Break when you have enough.
                * compute_indicators - compute indicators for poloniex (default)
                * compute_pair - BTC/USDT only 
                * backtest - backtest all strategies
                * ann - BE VERY VERY CAREFUL WITH THAT!!!! Because AI is our biggest existential threat.
            """))
