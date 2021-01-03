
import json

from flask import Flask, jsonify
from flask_redis import FlaskRedis
from werkzeug.exceptions import InternalServerError
from apscheduler.schedulers.background import BackgroundScheduler

# Flask app
app = Flask(__name__)
app.config.from_object('settings')
redis_client = FlaskRedis(app)


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


def _get_average_temperature():
    """Gets average temperature from two available sensors"""
    t1 = _get_sensor_temperature(app.config['DHT_PIN_16'])
    t2 = _get_sensor_temperature(app.config['DHT_PIN_20'])
    if t1 and t2:
        return (t1 + t2)/2


def _get_response(msg):
    """Wraps message into flask Response object"""
    return jsonify({"status": msg})


def _run_smart_controls():
    """Enables fans in case temperature goes above the threshold"""
    fans = _init_pwm()
    avg_temp = _get_average_temperature()
    if avg_temp and fans:
        if avg_temp > app.config['TEMPERATURE_THRESHOLD']:
            app.logger.info("Enabling fans the smart way based on temperature %sC" % str(avg_temp))
            fans.start(app.config['PWM_DEFAULT_DUTY'])
        else:
            app.logger.info("Disabling fans the smart way based on temperature %sC" % str(avg_temp))
            fans.stop()


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
    rpm_a6, rpm_a12 = _get_current_rpm()
    t1, t2 = _get_sensor_temperature(app.config['DHT_PIN_16']), _get_sensor_temperature(app.config['DHT_PIN_20'])
    stats = {
        "pwm_enabled": True if fans else False,
        "t1_temperature": t1,
        "t2_temperature": t2,
        "avg_temperature": (t1+t2)/2 if t1 and t2 else None,
        "pwm_duty_cycle": current_pwm_duty if fans else 0,
        "pwm_frequency": current_pwm_frequency if fans else 0,
        "rpm_a6": rpm_a6,
        "rpm_a12": rpm_a12,
    }
    
    return jsonify(stats)


@app.route("/test-redis")
def redis_test():
    return jsonify({"test": redis_client.get("test")})


if __name__ == "__main__":
    app.run(host='0.0.0.0')
