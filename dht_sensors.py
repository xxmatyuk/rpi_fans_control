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
        d = adafruit_dht.DHT22(pin, use_pulseio=False)
    except RuntimeError:
        d.exit()
        d = adafruit_dht.DHT22(pin, use_pulseio=False)
    return d


def _get_sensor_temperature(pin):
    """Gets tempreature mesure of a given sensor"""
    try:
        d = _get_dht_sensor(pin)
        if d:
            t = d.temperature
            d.exit()
            return t
    except Exception as e:
        if d:
            d.exit()

def _set_temperature(k, v):
    try:
        redis_client.set(k, v)
    except Exception:
        pass


def run_sensors_readings():
    while True:
        t1 = _get_sensor_temperature(settings.DHT_PIN_16)
        t2 = _get_sensor_temperature(settings.DHT_PIN_20)
        
        if t1:
            _set_temperature("current_t1_temp", t1)
        
        if t2:
            _set_temperature("current_t2_temp", t2)
        
        time.sleep(10)


if __name__ == "__main__":
    run_sensors_readings()
