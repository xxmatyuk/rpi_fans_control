import time
import atexit
import RPi.GPIO as GPIO

import settings

from redis_client import RedisClient

# GPIO initials
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Redis client wrapper
redis_client = RedisClient()

# Globals
fans = None


def _stop_pwm_fans_control():
    """Stops fans and does a cleanup"""
    global fans
    if fans:
        fans.stop()
        fans = None
    GPIO.cleanup()


def run_fans_controls():
    global fans
    while True:
        # Time to sleep
        time.sleep(3)

        # TODO: they come as bytes, fix that
        pwm_enabled = redis_client.get(settings.PWM_ENABLED_KEY)
        new_pwm_enabled = redis_client.get(settings.NEW_PWM_ENABLED_KEY)
        curr_ctrl_mode = redis_client.get(settings.CURR_CTRL_MODE)
        new_ctrl_mode = redis_client.get(settings.NEW_CTRL_MODE)
        curr_pwm_duty = redis_client.get(settings.CURR_PWM_DUTY)
        new_pwm_duty = redis_client.get(settings.NEW_PWM_DUTY)
        curr_t1_temp = redis_client.get(settings.CURR_T1_TEMP)
        curr_t2_temp = redis_client.get(settings.CURR_T2_TEMP)

        # PWM state has changed
        if pwm_enabled != new_pwm_enabled:
            if new_pwm_enabled == False:
                if fans:
                    fans.stop()
                GPIO.cleanup()
                redis_client.set(settings.PWM_ENABLED_KEY, False)
                fans = None
            else:
                GPIO.setup(settings.FANS_PIN, GPIO.OUT, initial=GPIO.LOW)
                fans = GPIO.PWM(settings.FANS_PIN, settings.PWM_DEFAULT_FREQ)
                fans.start(0)
                continue
        
        # PWM has not changed and it's disabled, do nothing
        if pwm_enabled == False:
            continue
            
        # PWM is enabled and control mode has changed
        if curr_ctrl_mode != new_ctrl_mode:
            if new_ctrl_mode == settings.MANUAL_MODE:
                redis_client.set(settings.CURR_CTRL_MODE, settings.MANUAL_MODE)
                continue
            else:
                redis_client.set(settings.CURR_CTRL_MODE, settings.AUTO_MODE)
                continue
            
        # Manual mode
        if curr_ctrl_mode == settings.MANUAL_MODE:
            if curr_pwm_duty == new_pwm_duty:
                continue
            else:
                if fans:
                    fans.ChangeDutyCycle(new_pwm_duty)
                    redis_client.set(settings.CURR_PWM_DUTY, new_pwm_duty)
                    continue
        
        # Auto mode
        if curr_ctrl_mode == settings.AUTO_MODE:
            if curr_t1_temp and curr_t2_temp:
                avg_temp = (curr_t1_temp + curr_t1_temp)/2
                if avg_temp > settings.TEMPERATURE_THRESHOLD and fans:
                    fans.ChangeDutyCycle(settings.PWM_DEFAULT_DUTY)
                    continue
                else:
                    fans.stop()
                    continue

# Do a clean-up
atexit.register(_stop_pwm_fans_control)

if __name__ == "__main__":
    run_fans_controls()
