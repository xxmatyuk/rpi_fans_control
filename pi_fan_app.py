
import atexit
import json

from http import HTTPStatus
from flask import Flask, jsonify, request, render_template, redirect
from werkzeug.exceptions import InternalServerError
from pystemd.systemd1 import Unit

from redis_client import RedisClient

# Flask app
app = Flask(__name__)
app.config.from_object('settings')

# Redis client
redis_client = RedisClient()


def _init_redis():
    """Fills Redis with default values"""
    redis_client.set_value(app.config["PWM_ENABLED"], False)
    redis_client.set_value(app.config["LIGHTS_ENABLED"], False)
    redis_client.set_value(app.config["NEW_LIGHTS_ENABLED"], False)
    redis_client.set_value(app.config["NEW_PWM_ENABLED"], False)
    redis_client.set_value(app.config["CURR_CTRL_MODE"], app.config["AUTO_MODE"])
    redis_client.set_value(app.config["NEW_CTRL_MODE"], app.config["AUTO_MODE"])
    redis_client.set_value(app.config["CURR_PWM_DUTY"], 0)
    redis_client.set_value(app.config["NEW_PWM_DUTY"], 0)
    redis_client.set_value(app.config["CURR_T1_TEMP"], -100.0)
    redis_client.set_value(app.config["CURR_T2_TEMP"], -100.0)


def _get_current_rpm(pwm_enabled, current_pwm_duty):
    """Returns RPM values based on PWM status and its values of duty"""

    if not pwm_enabled:
        return app.config['DEFAULT_RPM_A6'], app.config['DEFAULT_RPM_A12']
    elif pwm_enabled and current_pwm_duty == 0:
        return 0, 0
    elif pwm_enabled and current_pwm_duty == 100:
        return app.config['DEFAULT_RPM_A6'], app.config['DEFAULT_RPM_A12']
    else:
        return (
            (current_pwm_duty*app.config['DEFAULT_RPM_A6'])/100,
            (current_pwm_duty*app.config['DEFAULT_RPM_A12'])/100
        )


def _get_systemd_service_status(service_name):
    """Returns state of a given service"""
    unit = Unit(service_name)
    unit.load()
    return unit.Unit.ActiveState.decode("utf-8")


def _get_average_temperature():
    """Gets average temperature from two available sensors"""
    t1 = redis_client.current_t1_temperature
    t2 = redis_client.current_t2_temperature
    if t1 and t2:
        return (t1 + t2)/2


def _get_response(msg):
    """Wraps message into flask Response object"""
    return jsonify({"status": msg})


@app.errorhandler(InternalServerError)
def handle_500(e):
    """Internal server error handler"""
    response = e.get_response()
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


@app.route("/get-average-temperature", methods=['GET'])
def get_avg_temp():
    """Returns average pad temperature"""
    return str(_get_average_temperature())


@app.route("/pwm/enable", methods=['POST'])
def pwm_enable():
    """Enables PWM pad controls"""
    redis_client.set_value(app.config["CURR_TEMP_THRESHOLD"], app.config["DEFAULT_TEMPERATURE_THRESHOLD"])
    redis_client.set_value(app.config["NEW_TEMP_THRESHOLD"], app.config["DEFAULT_TEMPERATURE_THRESHOLD"])

    mode = request.args.get('mode', default=app.config["AUTO_MODE"], type=str)
    current_ctrl_mode = redis_client.current_ctrl_mode

    if redis_client.pwm_enabled and mode != current_ctrl_mode:
        redis_client.set_value(app.config["NEW_CTRL_MODE"], mode)
    elif not redis_client.pwm_enabled:
        redis_client.set_value(app.config["NEW_PWM_ENABLED"], True)
        redis_client.set_value(app.config["NEW_CTRL_MODE"], mode)
        redis_client.set_value(app.config["NEW_PWM_DUTY"], app.config["PWM_DEFAULT_DUTY"])

    return redirect("/", code=HTTPStatus.FOUND.value)


@app.route("/pwm/disable", methods=['POST'])
def pwm_disable():
    """Disables PWM pad controls"""
    if redis_client.pwm_enabled:
        redis_client.set_value(app.config["NEW_PWM_ENABLED"], False)
        redis_client.set_value(app.config["NEW_PWM_DUTY"], 0)

    return redirect("/", code=HTTPStatus.FOUND.value)


@app.route("/pwm/set-temp-threshold/<float:threshold>")
def pwm_set_temp_threshold(threshold, methods=['POST']):
    """Sets fan's enabling temperature threshold"""
    redis_client.set_value(app.config["NEW_TEMP_THRESHOLD"], threshold)
    return _get_response(app.config['TEMP_THRESHOLD_SET_MSG'])


@app.route("/pwm/set-duty/<int:percent>")
def pwm_set_duty(percent, methods=['POST']):
    """Sets PWM duty cycle"""
    if redis_client.pwm_enabled and redis_client.current_ctrl_mode == app.config["MANUAL_MODE"]:
        redis_client.set_value(app.config["NEW_PWM_DUTY"], percent)
        return _get_response(app.config['DUTY_SET_MSG'].format(pwm_duty=percent))

    return _get_response(app.config['NO_ACTION_MSG'])


@app.route("/pwm/stop-fans", methods=['POST'])
def stop_fans():
    """Explicitly stops fans"""
    if redis_client.pwm_enabled and redis_client.current_ctrl_mode == app.config["MANUAL_MODE"]:
        redis_client.set_value(app.config["NEW_PWM_DUTY"], 0)
        return _get_response(app.config['FANS_STOPPED_MSG'])

    return _get_response(app.config['NO_ACTION_MSG'])


@app.route("/lights/on", methods=['POST'])
def lights_on():
    """Turns light on"""
    if not redis_client.lights_enabled:
        redis_client.set_value(app.config["NEW_LIGHTS_ENABLED"], True)

    return redirect("/", code=HTTPStatus.FOUND.value)


@app.route("/lights/off", methods=['POST'])
def lights_off():
    """Turns light off"""
    if redis_client.lights_enabled:
        redis_client.set_value(app.config["NEW_LIGHTS_ENABLED"], False)

    return redirect("/", code=HTTPStatus.FOUND.value)


@app.route("/stats", methods=['GET'])
def stats_json():
    """Returns overal stats in JSON"""
    pwm_enabled = redis_client.pwm_enabled
    curr_ctrl_mode = redis_client.current_ctrl_mode
    curr_temp_threshold = redis_client.current_temperature_threshold
    current_pwm_duty = redis_client.current_pwm_duty
    t1 = redis_client.current_t1_temperature
    t2 = redis_client.current_t2_temperature
    rpm_a6, rpm_a12 = _get_current_rpm(pwm_enabled, current_pwm_duty)
    lights_enabled = redis_client.lights_enabled

    stats = {
        "sensors": {
            "t1_temperature": t1,
            "t2_temperature": t2,
            "avg_temperature": (t1+t2)/2 if t1 and t2 else None,
        },
        "controls": {
            "current_control_mode": curr_ctrl_mode,
            "current_temperature_threshold": curr_temp_threshold,
            "pwm_enabled": pwm_enabled,
            "lights_enabled": lights_enabled,
            "pwm_duty_cycle": current_pwm_duty,
        },
        "fans": {
            "rpm_a6": rpm_a6,
            "rpm_a12": rpm_a12,
        },
        "systemd_services": {
            app.config['DHT_SERVICE']: _get_systemd_service_status(app.config['DHT_SERVICE']),
            app.config['PWM_SERVICE']: _get_systemd_service_status(app.config['PWM_SERVICE']),
            app.config['WEB_APP_SERVICE']: _get_systemd_service_status(app.config['WEB_APP_SERVICE']),
        }
    }

    return jsonify(stats)


@app.route("/")
def index():
    """Index page"""
    pwm_enabled = redis_client.pwm_enabled
    curr_ctrl_mode = redis_client.current_ctrl_mode
    curr_temp_threshold = redis_client.current_temperature_threshold
    current_pwm_duty = redis_client.current_pwm_duty
    t1 = redis_client.current_t1_temperature
    t2 = redis_client.current_t2_temperature
    lights_enabled = redis_client.lights_enabled

    data = {
        "t1_temperature": t1,
        "t2_temperature": t2,
        "avg_temperature": (t1+t2)/2 if t1 and t2 else -100,
        "current_control_mode": curr_ctrl_mode,
        "current_temperature_threshold": curr_temp_threshold,
        "pwm_state": "enabled" if pwm_enabled else "disabled",
        "lights_state": "enabled" if lights_enabled else "disabled",
        "pwm_duty_cycle": "{}%".format(current_pwm_duty),
        "dht_deamon_state": _get_systemd_service_status(app.config['DHT_SERVICE']),
        "app_daemon_state": _get_systemd_service_status(app.config['PWM_SERVICE']),
        "pwm_daemon_state": _get_systemd_service_status(app.config['WEB_APP_SERVICE'])
    }
    
    return render_template("index.html", **data)


# Re-init redis just in case
atexit.register(_init_redis)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
