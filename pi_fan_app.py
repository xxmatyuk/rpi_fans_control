
import json

from flask import Flask, jsonify
from flask_redis import FlaskRedis
from werkzeug.exceptions import InternalServerError


# Flask app
app = Flask(__name__)
app.config.from_object('settings')

# Flask-redis client
redis_client = FlaskRedis(app)


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


def _get_average_temperature():
    """Gets average temperature from two available sensors"""
    t1 = redis_client.get(app.config["CURR_T1_TEMP"])
    t2 = redis_client.get(app.config["CURR_T2_TEMP"])
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


@app.route("/get-average-temperature")
def get_avg_temp():
    return str(_get_average_temperature())


@app.route("/pwm/enable")
def pwm_enable():
    pwm_enabled = redis_client.get(app.config["PWM_ENABLED_KEY"])
    if not pwm_enabled:
        redis_client.set(app.config["NEW_PWM_ENABLED_KEY"], True)
        redis_client.set(app.config["NEW_CTRL_MODE"], app.config["MANUAL_MODE"])
        redis_client.set(app.config["NEW_PWM_DUTY"], app.config["PWM_DEFAULT_DUTY"])
        return _get_response(app.config['PWM_ENABLED_MSG'])

    return _get_response(app.config['NO_ACTION_MSG'])


@app.route("/pwm/disable")
def pwm_enable():
    pwm_enabled = redis_client.get(app.config["PWM_ENABLED_KEY"])
    if pwm_enabled:
        redis_client.set(app.config["NEW_PWM_ENABLED_KEY"], False)
        redis_client.set(app.config["NEW_PWM_DUTY"], 0)
        return _get_response(app.config['PWM_DISABLED_MSG'])

    return _get_response(app.config['NO_ACTION_MSG'])


@app.route("/pwm/set-duty/<int:percent>")
def pwm_set_duty(percent):
    pwm_enabled = redis_client.get(app.config["PWM_ENABLED_KEY"])
    curr_ctrl_mode = redis_client.get(app.config["CURR_CTRL_MODE"])
    if pwm_enabled and curr_ctrl_mode == app.config["MANUAL_MODE"]:
        redis_client.set(app.config["NEW_PWM_DUTY"], percent)
        return _get_response(app.config['DUTY_SET_MSG'].format(pwm_duty=percent))

    return _get_response(app.config['NO_ACTION_MSG'])


@app.route("/pwm/stop-fans")
def stop_fans():
    pwm_enabled = redis_client.get(app.config["PWM_ENABLED_KEY"])
    curr_ctrl_mode = redis_client.get(app.config["CURR_CTRL_MODE"])

    if pwm_enabled and curr_ctrl_mode == app.config["MANUAL_MODE"]:
        redis_client.set(app.config["NEW_PWM_DUTY"], 0)
        return _get_response(app.config['FANS_STOPPED_MSG'])

    return _get_response(app.config['NO_ACTION_MSG'])


@app.route("/stats")
def stats():
    pwm_enabled = redis_client.get(app.config["PWM_ENABLED_KEY"])
    curr_ctrl_mode = redis_client.get(app.config["CURR_CTRL_MODE"])
    current_pwm_duty = redis_client.get(app.config["CURR_PWM_DUTY"])
    t1 = redis_client.get(app.config["CURR_T1_TEMP"])
    t2 = redis_client.get(app.config["CURR_T2_TEMP"])
    rpm_a6, rpm_a12 = _get_current_rpm(pwm_enabled, current_pwm_duty)
    stats = {
        "current_conttol_mode": curr_ctrl_mode,
        "pwm_enabled": pwm_enabled,
        "t1_temperature": t1,
        "t2_temperature": t2,
        "avg_temperature": (t1+t2)/2 if t1 and t2 else None,
        "pwm_duty_cycle": current_pwm_duty,
        "rpm_a6": rpm_a6,
        "rpm_a12": rpm_a12,
    }

    return jsonify(stats)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
