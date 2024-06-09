from dataclasses import dataclass
import functools
import json
import logging
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from tokenize import Double
from typing import Dict
from typing import Iterable
from typing import List
from typing import Tuple
from typing import Union

from decorators import prefixed_key

from redis import RedisError, from_url
from pydantic import BaseSettings


DEFAULT_KEY_PREFIX = "cache-key-prefix"
SENTIMENT_API_URL = "https://api.senticrypt.com/v1/bitcoin.json"
TWO_MINUTES = 60 + 60
HOURLY_BUCKET = "3600000"
DAILY_BUCKET = "86400000"
YEAR_HALF_HOURS = 14016


@dataclass
class SeriesItem:
    last: float
    rate: float
    mean: float
    median: float
    sum: float
    count: float
    timestamp: float
    btc_price: str


# Sentiments = List[Dict[str, Union[str, float]]]
Sentiments = List[SeriesItem]


class Config(BaseSettings):
    redis_url: str = "redis://redis:6379/0"


logging.basicConfig(
    format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S", level="DEBUG"
)
log = logging.getLogger(__name__)
config = Config()
redis = from_url(config.redis_url)


class Keys:
    """
    Methods to generate key names for Redis data structures.
    """

    def __init__(self, prefix: str = DEFAULT_KEY_PREFIX):
        self.prefix = prefix

    @prefixed_key
    def timeseries_sentiment_key(self) -> str:
        """
        A time series containing 30-second snapshots of BTC sentiment.
        """
        return f"sentiment:mean:30s"

    @prefixed_key
    def timeseries_price_key(self) -> str:
        """
        A time series containing 30-second snapshots of BTC price.
        """
        return f"price:mean:30s"

    @prefixed_key
    def cache_key(self) -> str:
        return f"cache"


def make_keys():
    return Keys()


async def add_many_to_timeseries(
    key_pairs: Iterable[Tuple[str, str]], data: Sentiments
):
    """
    Add many samples to a single timeseries key.

    `key_pairs` is an iteratble of tuples containing in the 0th position the
    timestamp key into which to insert entries and the 1th position the name
    of the key within th `data` dict to find the sample.

    example:
        ('cache-key-prefix:sentiment:mean:30s', 'mean')
        ('cache-key-prefix:price:mean:30s', 'btc_price')
        ---
        {'mean': 0.23, 'btc_price': '29089.35'}
    """
    data_points = []
    for datapoint in data:
        for timeseries_key, sample_key in key_pairs:
            data_points.append(
                (
                    timeseries_key,
                    int(float(datapoint["timestamp"]) * 1000),
                    datapoint[sample_key],
                )
            )
    madd_args = []
    for dp in data_points:
        madd_args.extend(dp)
    redis.execute_command("TS.MADD", *madd_args)


async def persist(keys: Keys, data: Sentiments):
    ts_sentiment_key = keys.timeseries_sentiment_key()
    ts_price_key = keys.timeseries_price_key()
    """
    ('cache-key-prefix:price:mean:30s', 'btc_price')
    ('cache-key-prefix:sentiment:mean:30s', 'mean')
    """
    await add_many_to_timeseries(
        (
            (ts_price_key, "btc_price"),
            (ts_sentiment_key, "mean"),
        ),
        data,
    )


def get_hourly_average(ts_key: str, top_of_the_hour: int):
    response = redis.execute_command(
        "TS.RANGE",
        ts_key,
        top_of_the_hour,
        "+",
        "AGGREGATION",
        "avg",
        DAILY_BUCKET,  # HOURLY_BUCKET,
    )
    # start_ts = 1627812000000  # Start timestamp
    # end_ts = 1627812300000    # End timestamp
    # response = redis.execute_command('TS.RANGE', ts_key, start_ts, end_ts)
    # Returns a list of the structure [timestamp, average].
    return response


def datetime_parser(dct):
    for k, v in dct.items():
        if isinstance(v, str) and v.endswith("+00:00"):
            try:
                dct[k] = datetime.datetime.fromisoformat(v)
            except:
                pass
    return dct


def get_cache(keys: Keys):
    current_hour_cache_key = keys.cache_key()
    current_hour_stats = redis.get(current_hour_cache_key)

    if current_hour_stats:
        return json.loads(current_hour_stats, object_hook=datetime_parser)


def set_cache(data, keys: Keys):
    def serialize_dates(v):
        return v.isoformat() if isinstance(v, datetime) else v

    redis.set(
        keys.cache_key(),
        json.dumps(data, default=serialize_dates),
        ex=TWO_MINUTES,
    )
    pass


def get_direction(last_three_hours, key: str):
    if len(last_three_hours) == 0:
        return "flat"

    if last_three_hours[0][key] < last_three_hours[-1][key]:
        return "rising"
    elif last_three_hours[0][key] > last_three_hours[-1][key]:
        return "falling"
    else:
        return "flat"


def now():
    """
    Wrap call to utcnow, so that we can mock this function in tests.
    """
    return datetime.utcnow()


def calculate_three_hours_of_data(keys: Keys) -> Dict[str, str]:
    sentiment_key = keys.timeseries_sentiment_key()
    price_key = keys.timeseries_price_key()
    three_hours_ago_ms = int(
        (now() - timedelta(hours=YEAR_HALF_HOURS)).timestamp() * 1000
    )
    # int((now() - timedelta(hours=3)).timestamp() * 1000)

    sentiment = get_hourly_average(sentiment_key, three_hours_ago_ms)
    price = get_hourly_average(price_key, three_hours_ago_ms)

    last_three_hours = [
        {
            "price": float(data[0][1]),
            "sentiment": float(data[1][1]),
            "time": datetime.fromtimestamp(data[0][0] / 1000, tz=timezone.utc),
        }
        for data in zip(price, sentiment)
    ]

    return {
        "hourly_average_of_averages": last_three_hours,
        "sentiment_direction": get_direction(last_three_hours, "sentiment"),
        "price_direction": get_direction(last_three_hours, "price"),
    }


async def make_timeseries(key: str):
    """
    Create a timeseries with the Redis key `key`.

    We'll use the duplicate policy known as "first," which ignores
    duplicate pairs of timestamp and values if we add them.

    Because of this, we don't worry about handling this logic
    ourselves -- but note that there is a performance cost to writes
    using this policy.
    """
    try:
        redis.execute_command(
            "TS.CREATE",
            key,
            "DUPLICATE_POLICY",
            "first",
        )
    except RedisError as e:
        log.debug("Could not create timeseries %s, error: %s", key, e)


async def initialize_redis(keys: Keys):
    await make_timeseries(keys.timeseries_sentiment_key())
    await make_timeseries(keys.timeseries_price_key())
