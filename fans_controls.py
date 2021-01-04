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
        time.sleep(settings.PWM_CTRL_TIMEOUT)

        # Get all values
        pwm_enabled = redis_client.pwm_enabled
        new_pwm_enabled = redis_client.new_pwm_enabled
        curr_ctrl_mode = redis_client.current_ctrl_mode
        new_ctrl_mode = redis_client.new_ctrl_mode
        curr_pwm_duty = redis_client.current_pwm_duty
        new_pwm_duty = redis_client.new_pwm_duty
        curr_t1_temp = redis_client.current_t1_temperature
        curr_t2_temp = redis_client.current_t2_temperature

        # PWM state has changed
        if pwm_enabled != new_pwm_enabled:
            if new_pwm_enabled == False:
                if fans:
                    fans.stop()
                GPIO.cleanup()
                redis_client.set_value(settings.PWM_ENABLED, False)
                fans = None
            else:
                redis_client.set_value(settings.PWM_ENABLED, True)
                GPIO.setup(settings.FANS_PIN, GPIO.OUT, initial=GPIO.LOW)
                fans = GPIO.PWM(settings.FANS_PIN, settings.PWM_DEFAULT_FREQ)
                fans.start(settings.PWM_DEFAULT_DUTY)
                continue
        
        # PWM has not changed and it's disabled, do nothing
        if pwm_enabled == False:
            continue
            
        # PWM is enabled and control mode has changed
        if curr_ctrl_mode != new_ctrl_mode:
            if new_ctrl_mode == settings.MANUAL_MODE:
                redis_client.set_value(settings.CURR_CTRL_MODE, settings.MANUAL_MODE)
                continue
            else:
                redis_client.set_value(settings.CURR_CTRL_MODE, settings.AUTO_MODE)
                continue
            
        # Manual mode
        if curr_ctrl_mode == settings.MANUAL_MODE:
            if curr_pwm_duty == new_pwm_duty:
                continue
            else:
                if fans:
                    fans.ChangeDutyCycle(new_pwm_duty)
                    redis_client.set_value(settings.CURR_PWM_DUTY, new_pwm_duty)
                    continue
        
        # Auto mode
        if curr_ctrl_mode == settings.AUTO_MODE:
            if curr_t1_temp and curr_t2_temp:
                avg_temp = (curr_t1_temp + curr_t1_temp)/2
                if avg_temp > settings.TEMPERATURE_THRESHOLD and fans:
                    fans.ChangeDutyCycle(settings.PWM_DEFAULT_DUTY)
                    redis_client.set_value(settings.CURR_PWM_DUTY, settings.PWM_DEFAULT_DUTY)
                    continue
                else:
                    fans.ChangeDutyCycle(0)
                    redis_client.set_value(settings.CURR_PWM_DUTY, 0)
                    continue

# Do a clean-up
atexit.register(_stop_pwm_fans_control)

if __name__ == "__main__":
    run_fans_controls()
