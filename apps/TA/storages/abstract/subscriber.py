from abc import ABC
import logging
from apps.TA import TAException

logger = logging.getLogger(__name__)


class SubscriberException(TAException):
    pass


class TASubscriber(ABC):
    classes_subscribing_to = []

    def __init__(self):
        from settings.redis_db import database
        self.database = database
        self.pubsub = database.pubsub()
        logger.info(f'New pubsub for {self.__class__.__name__}')
        for s_class in self.classes_subscribing_to:
            self.pubsub.subscribe(s_class.__name__)
            logger.info(f'{self.__class__.__name__} subscribed to '
                        f'{s_class.__name__} channel')

    def __call__(self):
        data_event = self.pubsub.get_message()
        if not data_event:
            return
        if not data_event.get('type') == 'message':
            return
        else:
            logger.debug(f'got message: {data_event}')

        # data_event = {
        #   'type': 'message',
        #   'pattern': None,
        #   'channel': b'channel',
        #   'data': b"dude, what's up?"
        # }

        try:
            channel_name = data_event['channel'].decode("utf-8")
            event_data = data_event['data'].decode("utf-8")
            logger.debug(f'handling event in {channel_name} subscription')
            self.handle(channel_name, event_data)
        except KeyError:
            logger.debug(f'unexpected format: {data_event}')
            pass  # message not in expected format. just ignore
        except Exception as e:
            raise SubscriberException(str(e))

    def handle(self, channel, data, *args, **kwargs):
        """
        overwrite me with some logic
        :return: None
        """
        logger.warning(f'NEW MESSAGE for '
                       f'{self.__class__.__name__} subscribed to '
                       f'{channel} channel '
                       f'BUT HANDLER NOT DEFINED! '
                       f'... message/event discarded')
        pass


def timestamp_is_near_5min(timestamp) -> bool:
    # close to a five minute period mark? (+ or - 45 seconds)
    seconds_from_five_min = (int(timestamp) + 45) % 300
    return bool(seconds_from_five_min < 90)


def get_nearest_5min_timestamp(timestamp) -> int:
    return ((int(timestamp) + 45) // 300) * 300
