# Fans
FANS_PIN = 21
PWM_DEFAULT_FREQ = 100
PWM_DEFAULT_DUTY = 88
DEFAULT_RPM_A6 = 3000
DEFAULT_RPM_A12 = 2000

# Sensors
DHT_PIN_16 = 16
DHT_PIN_20 = 20
TEMPERATURE_THRESHOLD = 24.1

# Response messages
NO_ACTION_MSG = "No action taken."
PWM_ENABLED_MSG = "Enabled."
PWM_DISABLED_MSG = "Disabled."
FANS_STOPPED_MSG = "Stopped."
CONTROLS_STOPPED_MSG = "Controls stopped."
DUTY_SET_MSG = "Duty is set to: {pwm_duty}"
FREQ_SET_MSG = "Frequency is set to: {pwm_frequency}"

# Redis
REDIS_URL = "redis://:@localhost:6379/0"
PWM_ENABLED = "pwm_enabled"
NEW_PWM_ENABLED = "new_pwm_enabled"
CURR_CTRL_MODE = "curr_ctrl_mode"
NEW_CTRL_MODE = "new_ctrl_mode"
CURR_PWM_DUTY = "curr_pwm_duty"
NEW_PWM_DUTY = "new_pwm_duty"
CURR_T1_TEMP = "curr_t1_temp"
CURR_T2_TEMP = "curr_t1_temp"

# Modes
MANUAL_MODE = 'manual'
AUTO_MODE = 'auto'