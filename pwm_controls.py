import time
import sys
import atexit
import RPi.GPIO as GPIO

import settings

from redis_client import RedisClient
from logger import logger

# GPIO initials
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Redis client wrapper
redis_client = RedisClient()

# Globals
fans = None
lights = None

def _stop_pwm_control():
    """Stops fans and does a cleanup"""
    global fans, lights
    if fans:
        fans.stop()
        fans = None
    
    if lights:
        lights.stop()
        lights = None

    GPIO.cleanup()


def run_pwm_controls():
    global fans, lights
    while True:
        # Time to sleep
        time.sleep(settings.PWM_CTRL_TIMEOUT)

        # Get all values
        pwm_enabled = redis_client.pwm_enabled
        new_pwm_enabled = redis_client.new_pwm_enabled
        lights_enabled = redis_client.lights_enabled
        new_lights_enabled = redis_client.new_lights_enabled
        curr_ctrl_mode = redis_client.current_ctrl_mode
        new_ctrl_mode = redis_client.new_ctrl_mode
        curr_pwm_duty = redis_client.current_pwm_duty
        new_pwm_duty = redis_client.new_pwm_duty
        curr_t1_temp = redis_client.current_t1_temperature
        curr_t2_temp = redis_client.current_t2_temperature
        curr_temp_threshold = redis_client.current_temperature_threshold
        new_temp_threshold = redis_client.new_temperature_threshold

        # Temperature threshold value has changed
        if curr_temp_threshold != new_temp_threshold:
            redis_client.set_value(settings.CURR_TEMP_THRESHOLD, new_temp_threshold)
            continue

        # Lights state has changed
        if lights_enabled != new_lights_enabled:
            redis_client.set_value(settings.LIGHTS_ENABLED, new_lights_enabled)
            if new_lights_enabled == False:
                if lights:
                    lights.start(0)
                continue
            else:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(settings.LIGHTS_PIN, GPIO.OUT, initial=GPIO.LOW)
                if not lights:
                    lights = GPIO.PWM(settings.LIGHTS_PIN, settings.LIGHT_DEFAULT_FREQ)
                lights.start(settings.LIGHTS_PWM_DEFAULT)
                continue

        # PWM state has changed
        if pwm_enabled != new_pwm_enabled:
            redis_client.set_value(settings.PWM_ENABLED, new_pwm_enabled)
            if new_pwm_enabled == False:
                if fans:
                    fans.stop()
                GPIO.cleanup()
                fans = None
                continue
            else:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(settings.FANS_PIN, GPIO.OUT, initial=GPIO.LOW)
                try:
                    fans = GPIO.PWM(settings.FANS_PIN, settings.PWM_DEFAULT_FREQ)
                except RuntimeError as e:
                    logger.error(str(e))
                fans.start(settings.PWM_DEFAULT_DUTY)
                continue

        # PWM is disabled, no need to go down below
        if pwm_enabled == False:
            continue

        # PWM is enabled and control mode has changed
        if curr_ctrl_mode != new_ctrl_mode:
            redis_client.set_value(settings.CURR_CTRL_MODE, new_ctrl_mode)
            continue

        # Manual mode
        if curr_ctrl_mode == settings.MANUAL_MODE and curr_pwm_duty != new_pwm_duty:
            redis_client.set_value(settings.CURR_PWM_DUTY, new_pwm_duty)
            if fans:
                fans.ChangeDutyCycle(new_pwm_duty)
                continue

        # Auto mode
        if curr_ctrl_mode == settings.AUTO_MODE and curr_t1_temp and curr_t2_temp:
            avg_temp = (curr_t1_temp + curr_t2_temp)/2
            if fans:
                if avg_temp > curr_temp_threshold + 2:
                    fans.ChangeDutyCycle(100)
                    redis_client.set_value(settings.CURR_PWM_DUTY, 100)
                    continue
                elif avg_temp > curr_temp_threshold+1:
                    duty = settings.PWM_DEFAULT_DUTY + 5
                    fans.ChangeDutyCycle(duty)
                    redis_client.set_value(settings.CURR_PWM_DUTY, duty)
                    continue
                elif avg_temp > curr_temp_threshold:
                    fans.ChangeDutyCycle(settings.PWM_DEFAULT_DUTY)
                    redis_client.set_value(settings.CURR_PWM_DUTY, settings.PWM_DEFAULT_DUTY)
                    continue
                else:
                    fans.ChangeDutyCycle(0)
                    redis_client.set_value(settings.CURR_PWM_DUTY, 0)
                    continue


# Do a clean-up
atexit.register(_stop_pwm_control)

if __name__ == "__main__":
    try:
        run_pwm_controls()
    except Exception as e:
        logger.exception(str(e))
        sys.exit(1)
