import redis

import settings

class RedisClient:

    def __init__(self, user=None, password=None, host='localhost', port=6379, db=0):
        self._conn = redis.Redis(host=host, port=port, db=db, charset="utf-8", decode_responses=True)


    def _set(self, k, v):
        self._conn.set(k, v)


    def _get(self, k):
        return self._conn.get(k)


    def set_value(self, k, v):
        if type(v) != str:
            v = str(v)
        self._set(k, v)


    @property
    def pwm_enabled(self):
        try:
            return True if self._get(settings.PWM_ENABLED) == "True" else False
        except (TypeError, ValueError):
            return None


    @property
    def new_pwm_enabled(self):
        try:
            return True if self._get(settings.NEW_PWM_ENABLED) == "True" else False
        except (TypeError, ValueError):
            return None


    @property
    def current_ctrl_mode(self):
        return self._get(settings.CURR_CTRL_MODE)


    @property
    def new_ctrl_mode(self):
        return self._get(settings.NEW_CTRL_MODE)


    @property
    def current_pwm_duty(self):
        try:
            return int(self._get(settings.CURR_PWM_DUTY))
        except (TypeError, ValueError):
            return None


    @property
    def new_pwm_duty(self):
        try:
            return int(self._get(settings.NEW_PWM_DUTY))
        except (TypeError, ValueError):
            return None


    @property
    def current_t1_temperature(self):
        try:
            return float(self._get(settings.CURR_T1_TEMP))
        except (TypeError, ValueError):
            return None


    @property
    def current_t2_temperature(self):
        try:
            return float(self._get(settings.CURR_T2_TEMP))
        except (TypeError, ValueError):
            return None