import atexit
import json
import adafruit_dht
import RPi.GPIO as GPIO

from flask import Flask, jsonify
from werkzeug.exceptions import InternalServerError

# Flask stuff
app = Flask(__name__)
app.config.from_object('settings')

# Global vars
fans = None
current_pwm_duty = None
current_pwm_frequency = None

# TODO:
# 1. add "smart" part via Flask cronjobs
# 2. add all the installation part to readme

def _get_dht_sensor(pin):
    """Returns DHT sesnor instance"""
    d = None
    try:
        d = adafruit_dht.DHT22(pin)
    except RuntimeError:
        app.logger.error("Unable to initialize DHT sensor. Re-trying.")
        d.exit()
        d = adafruit_dht.DHT22(pin)
    return d


def _init_pwm():
    """Inits PWM fans controls"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(app.config['FANS_PIN'], GPIO.OUT, initial=GPIO.LOW)
    
    global fans
    fans = GPIO.PWM(app.config['FANS_PIN'], app.config['PWM_DEFAULT_FREQ'])
    

def _stop_fans():
    """Stops fans without loosing controls"""
    global fans, current_pwm_duty
    if fans:
        fans.stop()
        current_pwm_duty = 0


def _stop_pwm_fans_control():
    """Stops fans and does cleanup"""
    global fans
    _stop_fans()
    GPIO.cleanup()
    fans = None


def _set_fans_pwm_duty_cycle(percent):
    """Sets fans' duty cycle"""
    global fans, current_pwm_duty
    if fans:
        fans.ChangeDutyCycle(percent)
        current_pwm_duty = percent


def _set_fans_pwm_frequency(freq):
    """Sets fans' frequency"""
    global fans, current_pwm_frequency
    if fans:
        fans.ChangeFrequency(freq)
        current_pwm_frequency = freq


def _get_current_rpm():
    """Returns RPM values based on PWM status and its values of duty and frequency"""
    global fans, current_pwm_duty
    if not fans:
        return app.config['DEFAULT_RPM_A6'], app.config['DEFAULT_RPM_A12']
    elif fans and current_pwm_duty == 0:
        return 0, 0
    elif fans and current_pwm_duty == 100:
        return app.config['DEFAULT_RPM_A6'], app.config['DEFAULT_RPM_A12']
    else:
        return (
            (current_pwm_duty*app.config['DEFAULT_RPM_A6'])/100, 
            (current_pwm_duty*app.config['DEFAULT_RPM_A12'])/100
        )


def _get_sensor_temperature(pin):
    """Gets tempreature mesure of a given sensor"""
    try:
        d = _get_dht_sensor(pin)
        if d:
            t = d.temperature
            d.exit()
            return t
    except Exception as e:
        app.logger.error("Unable to read temperature from pin %i. Error: %s" % (pin, str(e)))
        if d:
            d.exit()
        return -100


def _get_average_temperature():
    """Gets average temperature from two available sensors"""
    t1 = _get_sensor_temperature(app.config['DHT_PIN_16'])
    t2 = _get_sensor_temperature(app.config['DHT_PIN_20'])
    if t1 and t2:
        return (t1 + t2)/2


def _get_response(msg):
    """Wraps message into flask Response object"""
    return jsonify({"status": msg})


@app.errorhandler(InternalServerError)
def handle_500(e):
    response = e.get_response()
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


@app.route("/get-sensor-temperature/<int:pin>")
def get_sensor_temp(pin):
    return str(_get_sensor_temperature(pin))


@app.route("/get-average-temperature")
def get_avg_temp():
    return str(_get_average_temperature())


@app.route("/pwm/start")
def pwm_start():
    global fans, current_pwm_duty, current_pwm_frequency
    try:
        _init_pwm()
        fans.start(app.config['PWM_DEFAULT_DUTY'])
        current_pwm_duty = app.config['PWM_DEFAULT_DUTY']
        current_pwm_frequency = app.config['PWM_DEFAULT_FREQ']
        
        return _get_response(app.config['PWM_STARTED_MSG'])
    except RuntimeError:
        app.logger.error("Failed to start PWM")

    return _get_response(app.config['NO_ACTION_MSG'])

@app.route("/pwm/set-duty/<int:percent>")
def pwm_set_duty(percent):
    global fans, current_pwm_duty
    if fans:
        _set_fans_pwm_duty_cycle(percent)
        return _get_response(app.config['DUTY_SET_MSG'].format(pwm_duty=current_pwm_duty))

    return _get_response(app.config['NO_ACTION_MSG'])


@app.route("/pwm/set-frequency/<int:freq>")
def pwm_set_frequency(freq):
    global fans, current_pwm_frequency
    if fans:
        _set_fans_pwm_frequency(freq)
        return _get_response(app.config['FREQ_SET_MSG'].format(pwm_frequency=current_pwm_frequency))

    return _get_response(app.config['NO_ACTION_MSG'])


@app.route("/pwm/stop-fans")
def stop_fans():
    global fans
    if fans:
        _stop_fans()
        return _get_response(app.config['FANS_STOPPED_MSG'])

    return _get_response(app.config['NO_ACTION_MSG'])


@app.route("/pwm/cleanup")
def pwm_cleanup():
    global fans
    if fans:
        _stop_pwm_fans_control()
        return _get_response(status=app.config['CONTROLS_STOPPED_MSG'])

    return _get_response(app.config['NO_ACTION_MSG'])


@app.route("/stats")
def stats():
    global fans, current_pwm_duty, current_pwm_frequency
    rpm_a6, rpm_a12 = _get_current_rpm()
    t1, t2 = _get_sensor_temperature(app.config['DHT_PIN_16']), _get_sensor_temperature(app.config['DHT_PIN_20'])
    stats = {
        "pwm_enabled": True if fans else False,
        "t1_temperature": t1,
        "t2_temperature": t2,
        "avg_temperature": (t1+t2)/2,
        "pwm_duty_cycle": current_pwm_duty if fans else 0,
        "pwm_frequency": current_pwm_frequency if fans else 0,
        "rpm_a6": rpm_a6,
        "rpm_a12": rpm_a12,
    }
    
    return jsonify(stats)


atexit.register(_stop_pwm_fans_control)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
