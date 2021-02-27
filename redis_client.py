import redis

import settings

class RedisClient:

    """Wrapper class for redis client"""

    def __init__(self, user=None, password=None, host='localhost', port=6379, db=0):
        self._conn = redis.Redis(host=host, port=port, db=db, charset="utf-8", decode_responses=True)


    def _set(self, k, v):
        self._conn.set(k, v)


    def _get(self, k):
        return self._conn.get(k)


    def _get_typed_value(self, v, t):
        try:
            return t(v)
        except (TypeError, ValueError):
            return None


    def set_value(self, k, v):
        if type(v) != str:
            v = str(v)
        self._set(k, v)

    @property
    def lights_enabled(self):
        return True if self._get(settings.LIGHTS_ENABLED) == "True" else False

    @property
    def new_lights_enabled(self):
        return True if self._get(settings.NEW_LIGHTS_ENABLED) == "True" else False

    @property
    def pwm_enabled(self):
        return True if self._get(settings.PWM_ENABLED) == "True" else False

    @property
    def new_pwm_enabled(self):
        return True if self._get(settings.NEW_PWM_ENABLED) == "True" else False

    @property
    def current_ctrl_mode(self):
        return self._get(settings.CURR_CTRL_MODE)

    @property
    def new_ctrl_mode(self):
        return self._get(settings.NEW_CTRL_MODE)

    @property
    def current_pwm_duty(self):
        return self._get_typed_value(self._get(settings.CURR_PWM_DUTY), int)

    @property
    def new_pwm_duty(self):
        return self._get_typed_value(self._get(settings.NEW_PWM_DUTY), int)

    @property
    def current_t1_temperature(self):
        return self._get_typed_value(self._get(settings.CURR_T1_TEMP), float)

    @property
    def current_t2_temperature(self):
        return self._get_typed_value(self._get(settings.CURR_T2_TEMP), float)

    @property
    def current_temperature_threshold(self):
        return self._get_typed_value(self._get(settings.CURR_TEMP_THRESHOLD), float)

    @property
    def new_temperature_threshold(self):
        return self._get_typed_value(self._get(settings.NEW_TEMP_THRESHOLD), float)
