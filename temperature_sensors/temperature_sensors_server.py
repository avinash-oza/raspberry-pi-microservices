import time
import datetime
import json
import ConfigParser

from bottle import route, run, template, auth_basic
import RPi.GPIO as GPIO
from sensors_lib.get_temperature import get_ds18b20_sensor

config = ConfigParser.RawConfigParser()
config.read('temperature_sensors.config')

# The output is kept the same as the nagios passive check plugin so that this result can be submitted directly

# Get the senors and zip them to make a dict
sensor_names = config.get('general','sensor_names').split(',')
sensor_ids = config.get('general','sensor_ids').split(',')
TEMPERATURE_SENSOR_MAPPING = dict(zip(sensor_names, sensor_ids))

SORTED_KEYS = [k for k in sorted(TEMPERATURE_SENSOR_MAPPING)] # Sort keys so order is the same
CRITICAL_TEMP = float(config.get('general', 'critical_temperature'))
hostname = config.get('general', 'hostname')

# Bottle related logic

@route('/temperature/<sensor_name>')
def temperature_route(sensor_name):
    response = []
    if sensor_name == 'all':
        sensor_names = SORTED_KEYS
    else:
        sensor_names = [sensor_name]

    for one_sensor in sensor_names:
        one_response = {}
        try:
            sensor_temp, error = get_ds18b20_sensor(TEMPERATURE_SENSOR_MAPPING[one_sensor], critical_temp=CRITICAL_TEMP)
        except:
            sensor_temp = 'ERROR OCCURED FOR {0}".format(one_sensor)'
            error = 2 # Critcal status

        one_response['sensor_name'] = one_sensor
        one_response['raw_value'] = sensor_temp
        one_response['service_description'] = "{0} Temperature".format(one_sensor.capitalize())
        one_response['plugin_output'] = "{0} Temperature: {1}F".format(one_sensor.capitalize(), sensor_temp)
        one_response['return_code'] = str(error)
        one_response['status_time'] = datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        one_response['hostname'] = hostname

        response.append(one_response)

    return json.dumps(response)

port_number = int(config.get('general', 'port'))
run(host='0.0.0.0', port=port_number)
