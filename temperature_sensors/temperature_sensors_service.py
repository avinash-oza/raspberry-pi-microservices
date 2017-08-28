import time
import datetime
import json
import ConfigParser

from bottle import route, run, template, auth_basic
import RPi.GPIO as GPIO
from .sensors_lib import get_ds18b20_sensor

config = ConfigParser.RawConfigParser()
config.read('garage_door.config')


# Pi specific constants relative to looking at the house
TEMPERATURE_SENSOR_MAPPING = {'CASE': '28-05167155beff'}
SORTED_KEYS = [k for k in sorted(TEMPERATURE_SENSOR_MAPPING)] # Sort keys so order is the same

#ef setup_pins():
#   GPIO.setmode(GPIO.BCM)
#   for one_pin in RELAY_PIN_MAPPING.values():
#       GPIO.setup(one_pin, GPIO.OUT)

#   for one_pin in GARAGE_SENSOR_MAPPING.values():
#       GPIO.setup(one_pin, GPIO.IN)

#ef get_garage_status(garage_name):
#   error = True # Start by default with error
#   try:
#       pin_result = GPIO.input(GARAGE_SENSOR_MAPPING[garage_name])
#   except KeyError:
#       garage_status = 'INVALID GARAGE NAME'
#   else:
#       if pin_result == 0:
#           garage_status = 'CLOSED'
#           error = False
#       elif pin_result == 1:
#           garage_status = 'OPEN'
#           error = False
#       else:
#           garage_status = 'UNKNOWN'

#   return garage_status, error

#ef control_garage(garage_name, action):
#   # action is (OPEN, CLOSE)
#   action_error = True
#   if garage_name not in RELAY_PIN_MAPPING:
#       message = 'INVALID GARAGE_NAME'
#       return message, action_error

#   if action not in ('OPEN', 'CLOSE'):
#       message = 'INVALID ACTION'
#       return message, action_error

#   # Check what the current location is
#   current_garage_status, status_error = get_garage_status(garage_name)
#   if current_garage_status == 'OPEN' and action == 'OPEN':
#       message = 'Trying to open garage that is already open'
#   elif current_garage_status == 'CLOSED' and action == 'CLOSE':
#       message = 'Trying to close garage that is already closed'
#   else:
#       relay_pin = RELAY_PIN_MAPPING[garage_name]
#       try:
#           GPIO.output(relay_pin,GPIO.HIGH)
#           time.sleep(0.5)
#           GPIO.output(relay_pin,GPIO.LOW)
#       except:
#           message = 'AN ERROR OCCURED WHILE TRIGGERING THE RELAY'
#       else:
#           action_error = False
#           message = 'TRIGGERED {0} GARAGE TO {1}. OLD POSITION: {2}'.format(garage_name, action, current_garage_status)

#   return message, action_error


# Bottle related logic

@route('/temperature/<sensor_name>')
def garage_status_route(sensor_name):
    response = []
    sensor_name = [sensor_name]

    for one_sensor in sensor_name:
        one_response = {}
        garage_status, error = get_ds18b20_sensor(one_sensor, critical_temp=73)

        one_response['sensor_name'] = one_garage
        one_response['error'] = error
        one_response['status_time'] = datetime.datetime.now().strftime('%I:%M:%S%p')

        response.append(one_response)

    return json.dumps(response)

#route('/garage/control/<garage_name>/<current_status>')
#auth_basic(basic_auth_check)
#ef garage_control_route(garage_name, current_status):
#   response = {}
#   response['status_time'] = datetime.datetime.now().strftime('%I:%M:%S%p')

#   message, error = control_garage(garage_name, current_status)

#   response.update({'status': message, 'error': error})
#   return json.dumps(response)

#ry:
#   setup_pins()
#ort_number = int(config.get('general', 'port'))
run(host='0.0.0.0', port=26000)
#inally:
#   GPIO.cleanup()
