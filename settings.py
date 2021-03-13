# Fans
FANS_PIN = 21
PWM_DEFAULT_FREQ = 100
PWM_DEFAULT_DUTY = 88
DEFAULT_RPM_A6 = 3000
DEFAULT_RPM_A12 = 2000
PWM_CTRL_TIMEOUT = 1

# Lights
LIGHTS_PIN = 12
LIGHTS_PWM_DEFAULT = 100
LIGHT_DEFAULT_FREQ = 100

# Sensors
DHT_PIN_16 = 16
DHT_PIN_20 = 20
DEFAULT_TEMPERATURE_THRESHOLD = 25.1
DHT_POLLING_TIMEOUT_SECONDS = 5

# Systemd servces names
DHT_SERVICE = "dht_sensors.service"
PWM_SERVICE = "pwm_controls.service"
WEB_APP_SERVICE = "pi_fan_app.service"

# Response messages
NO_ACTION_MSG = "No action taken."
PWM_ENABLED_MSG = "Enabled."
PWM_DISABLED_MSG = "Disabled."
FANS_STOPPED_MSG = "Stopped."
CONTROLS_STOPPED_MSG = "Controls stopped."
DUTY_SET_MSG = "Duty is set to: {pwm_duty}."
FREQ_SET_MSG = "Frequency is set to: {pwm_frequency}."
LIGHTS_ON_MSG = "Lights are enabled."
LIGHTS_OFF_MSG = "Lights are disabled."
TEMP_THRESHOLD_SET_MSG = "New temperature threshold is set."
UNABLE_TO_SET_PROP_MSG = "Unable to set {}"

# Redis URL
REDIS_URL = "redis://:@localhost:6379/0"

# Redis variables and client properties. Mind that each value corresponds to the client"s property name.
PWM_ENABLED = "pwm_enabled"
NEW_PWM_ENABLED = "new_pwm_enabled"
CURR_CTRL_MODE = "current_ctrl_mode"
NEW_CTRL_MODE = "new_ctrl_mode"
CURR_PWM_DUTY = "current_pwm_duty"
NEW_PWM_DUTY = "new_pwm_duty"
CURR_T1_TEMP = "current_t1_temperature"
CURR_T2_TEMP = "current_t2_temperature"
LIGHTS_ENABLED = "lights_enabled"
NEW_LIGHTS_ENABLED = "new_lights_enabled"
CURR_TEMP_THRESHOLD = "current_temperature_threshold"
NEW_TEMP_THRESHOLD = "new_temperature_threshold"

# Modes
MANUAL_MODE = "manual"
AUTO_MODE = "auto"

# Mics
POLLING_INTERVAL = 0.2
SET_AND_WAIT_TIMEOUT = 2
AVG_TEMP = "average_temperature"