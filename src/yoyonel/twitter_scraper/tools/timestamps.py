import datetime as dt

import datetime as datetime
from dateutil import parser
from dateutil.tz import gettz

EPOCH_AWARE = dt.datetime.fromtimestamp(0, dt.timezone.utc)


def unix_timestamp_ms_to_datetime(timestamp):
    """
    Convert milliseconds since epoch UTC to datetime

    :param timestamp: a unix timestamp in milliseconds
    :type timestamp: int

    :return: A datetime object matching the timestamp
    :rtype: datetime.datetime
    """

    diff = ((timestamp % 1000) + 1000) % 1000
    seconds = (timestamp - diff) / 1000
    micros = diff * 1000
    return EPOCH_AWARE + dt.timedelta(seconds=seconds, microseconds=micros)


def parse_to_timestamp(timestr: str) -> int:
    """

    Args:
        timestr:

    Returns:

    """
    return int(parser.parse(timestr).timestamp() * 1000)


def tweet_datetime_to_utc_timestamp(tweet_datetime: int,
                                    tweet_timezone: str) -> int:
    """

    Args:
        tweet_datetime:
        tweet_timezone:

    Returns:

    """
    # https://stackoverflow.com/questions/79797/how-to-convert-local-time-string-to-utc
    return int(
        unix_timestamp_ms_to_datetime(tweet_datetime).
        astimezone(gettz(tweet_timezone)).
        replace(tzinfo=None).
        timestamp() * 1000
    )
