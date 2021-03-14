
import atexit
import json
import time

from datetime import datetime

from http import HTTPStatus
from flask import Flask, jsonify, request, render_template, redirect
from werkzeug.exceptions import InternalServerError
from pystemd.systemd1 import Unit

from redis_client import RedisClient
from logger import logger

# Flask app
app = Flask(__name__)
app.config.from_object("settings")

# Redis client
redis_client = RedisClient()

OK = HTTPStatus.OK.value
BAD_REQUEST = HTTPStatus.BAD_REQUEST.value
INTERNAL_SERVER_ERROR = HTTPStatus.INTERNAL_SERVER_ERROR.value


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
        return app.config["DEFAULT_RPM_A6"], app.config["DEFAULT_RPM_A12"]
    elif pwm_enabled and current_pwm_duty == 0:
        return 0, 0
    elif pwm_enabled and current_pwm_duty == 100:
        return app.config["DEFAULT_RPM_A6"], app.config["DEFAULT_RPM_A12"]
    else:
        return (
            (current_pwm_duty*app.config["DEFAULT_RPM_A6"])/100,
            (current_pwm_duty*app.config["DEFAULT_RPM_A12"])/100
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


def _get_response(msg, status=OK):
    """Wraps message into flask Response object with 200 OK status"""
    return jsonify({"status": msg}), status


def _get_error_response(msg):
    """Wraps message into flask Response object with 500 Interal server error status"""
    json, _ = _get_response(msg)
    return json, INTERNAL_SERVER_ERROR


def _set_and_wait(k, v):
    """Sets the given value provided by key and wait until it"s set or failed."""
    try:
        redis_client.set_value(k, v)
        start = datetime.now()
        delta = 0
        while delta < app.config["SET_AND_WAIT_TIMEOUT"]:
            time.sleep(app.config["POLLING_INTERVAL"])
            if getattr(redis_client, k) == v:
                return True
            delta = (datetime.now() - start).seconds
    except Exception as e:
        logger.error(str(e))


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


@app.route("/get-average-temperature", methods=["GET"])
def get_avg_temp():
    """Returns average pad temperature"""
    return str(_get_average_temperature())


@app.route("/pwm/enable/<string:mode>", methods=["POST"])
def pwm_enable(mode):
    """Enables PWM pad controls"""
    if mode not in ["auto", "manual"]:
        return _get_response(app.config["BAD_MODE_MSG"], status=BAD_REQUEST)

    current_ctrl_mode = redis_client.current_ctrl_mode
    pwm_enabled = redis_client.pwm_enabled

    if not _set_and_wait(app.config["CURR_TEMP_THRESHOLD"], app.config["DEFAULT_TEMPERATURE_THRESHOLD"]):
        return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["CURR_TEMP_THRESHOLD"]))
    if not _set_and_wait(app.config["NEW_TEMP_THRESHOLD"], app.config["DEFAULT_TEMPERATURE_THRESHOLD"]):
        return _get_error_response(
            app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_TEMP_THRESHOLD"]))

    if pwm_enabled and mode != current_ctrl_mode:
        if not _set_and_wait(app.config["NEW_CTRL_MODE"], mode):
            return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_CTRL_MODE"]))
        return _get_response(app.config["PWM_ENABLED_MSG"])
    elif not pwm_enabled:
        if not _set_and_wait(app.config["NEW_PWM_ENABLED"], True):
            return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_PWM_ENABLED"]))
        if not _set_and_wait(app.config["NEW_CTRL_MODE"], mode):
            return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_CTRL_MODE"]))
        if not _set_and_wait(app.config["NEW_PWM_DUTY"], app.config["PWM_DEFAULT_DUTY"]):
            return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_PWM_DUTY"]))
        return _get_response(app.config["PWM_ENABLED_MSG"])

    return _get_response(app.config["NO_ACTION_MSG"])


@app.route("/pwm/disable", methods=["POST"])
def pwm_disable():
    """Disables PWM pad controls"""
    if redis_client.pwm_enabled:
        if not _set_and_wait(app.config["NEW_PWM_ENABLED"], False):
            return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_PWM_ENABLED"]))
        if not _set_and_wait(app.config["NEW_PWM_DUTY"], 0):
            return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_PWM_DUTY"]))
        return _get_response(app.config["PWM_DISABLED_MSG"])

    return _get_response(app.config["NO_ACTION_MSG"])


@app.route("/pwm/set-temp-threshold/<string:threshold>")
def pwm_set_temp_threshold(threshold, methods=["POST"]):
    """Sets fan"s enabling temperature threshold"""
    try:
        threshold = float(threshold)
    except ValueError:
        return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_TEMP_THRESHOLD"]))

    if not _set_and_wait(app.config["NEW_TEMP_THRESHOLD"], threshold):
        return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_TEMP_THRESHOLD"]))

    return _get_response(app.config["TEMP_THRESHOLD_SET_MSG"])


@app.route("/pwm/set-duty/<int:percent>")
def pwm_set_duty(percent, methods=["POST"]):
    """Sets PWM duty cycle"""
    if redis_client.pwm_enabled and redis_client.current_ctrl_mode == app.config["MANUAL_MODE"]:
        if not _set_and_wait(app.config["NEW_PWM_DUTY"], percent):
            return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_PWM_DUTY"]))
        return _get_response(app.config["DUTY_SET_MSG"].format(pwm_duty=percent))

    return _get_response(app.config["NO_ACTION_MSG"])


@app.route("/pwm/stop-fans", methods=["POST"])
def stop_fans():
    """Explicitly stops fans"""
    if redis_client.pwm_enabled and redis_client.current_ctrl_mode == app.config["MANUAL_MODE"]:
        if not _set_and_wait(app.config["NEW_PWM_DUTY"], 0):
            return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_PWM_DUTY"]))
        return _get_response(app.config["FANS_STOPPED_MSG"])

    return _get_response(app.config["NO_ACTION_MSG"])


@app.route("/lights/on", methods=["POST"])
def lights_on():
    """Turns light on"""
    if not redis_client.lights_enabled:
        if not _set_and_wait(app.config["NEW_LIGHTS_ENABLED"], True):
            return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_LIGHTS_ENABLED"]))
        return _get_response(app.config["LIGHTS_ON_MSG"])

    return _get_response(app.config["NO_ACTION_MSG"])


@app.route("/lights/off", methods=["POST"])
def lights_off():
    """Turns light off"""
    if redis_client.lights_enabled:
        if not _set_and_wait(app.config["NEW_LIGHTS_ENABLED"], False):
            return _get_error_response(app.config.get("UNABLE_TO_SET_PROP_MSG").format(app.config["NEW_LIGHTS_ENABLED"]))
        return _get_response(app.config["LIGHTS_OFF_MSG"])

    return _get_response(app.config["NO_ACTION_MSG"])


@app.route("/stats", methods=["GET"])
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
            app.config["DHT_SERVICE"]: _get_systemd_service_status(app.config["DHT_SERVICE"]),
            app.config["PWM_SERVICE"]: _get_systemd_service_status(app.config["PWM_SERVICE"]),
            app.config["WEB_APP_SERVICE"]: _get_systemd_service_status(app.config["WEB_APP_SERVICE"]),
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
        app.config["CURR_CTRL_MODE"]: curr_ctrl_mode,
        app.config["CURR_TEMP_THRESHOLD"]: curr_temp_threshold,
        app.config["LIGHTS_ENABLED"]: lights_enabled,
        app.config["PWM_ENABLED"]: pwm_enabled,
        app.config["CURR_PWM_DUTY"]: "{}%".format(current_pwm_duty),
        app.config["CURR_T1_TEMP"]: t1,
        app.config["CURR_T2_TEMP"]: t2,
        app.config["AVG_TEMP"]: (t1+t2)/2 if t1 and t2 else None,
        app.config["DHT_SERVICE"]: _get_systemd_service_status(app.config["DHT_SERVICE"]),
        app.config["PWM_SERVICE"]: _get_systemd_service_status(app.config["PWM_SERVICE"]),
        app.config["WEB_APP_SERVICE"]: _get_systemd_service_status(app.config["WEB_APP_SERVICE"])
    }

    return render_template("index.html", data=data)


# Re-init redis just in case
atexit.register(_init_redis)

if __name__ == "__main__":
    app.run(host="0.0.0.0")
