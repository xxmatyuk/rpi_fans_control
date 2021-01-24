import time
import sys
import adafruit_dht

import settings

from redis_client import RedisClient

# Redis client wrapper
redis_client = RedisClient()


def _get_dht_sensor(pin):
    """Returns DHT sesnor instance"""
    d = None
    try:
        d = adafruit_dht.DHT22(pin)
    except RuntimeError:
        d.exit()
        d = adafruit_dht.DHT22(pin)
    return d


def _get_sensor_temperature(pin):
    """Gets tempreature mesure of a given sensor"""
    try:
        d = _get_dht_sensor(pin)
        if d:
            t = d.temperature
            d.exit()
            return t
    except:
        if d:
            d.exit()
        raise


def run_sensors_readings():
    while True:
        t1 = _get_sensor_temperature(settings.DHT_PIN_16)
        t2 = _get_sensor_temperature(settings.DHT_PIN_20)
        
        if t1:
            redis_client.set_value(settings.CURR_T1_TEMP, t1)
        
        if t2:
            redis_client.set_value(settings.CURR_T2_TEMP, t2)
        
        time.sleep(settings.DHT_POLLING_TIMEOUT_SECONDS)


if __name__ == "__main__":
    try:
        run_sensors_readings()
    except:
        sys.exit(1)
