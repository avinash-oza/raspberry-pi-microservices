import time
import datetime
import json
import configparser
import requests

from flask import Flask, request
from flask_restplus import Api, Resource
import boto3
import RPi.GPIO as GPIO

config = configparser.ConfigParser()
config.read('garage_door.config')

hostname = config.get('general', 'hostname')

app = Flask(__name__)
api = Api(app)


# Pi specific constants relative to looking at the house
RELAY_PIN_MAPPING = {'LEFT' : 27, 'RIGHT': 22} 
GARAGE_SENSOR_MAPPING = {'LEFT': 25, 'RIGHT': 16}
SORTED_KEYS = [k for k in sorted(RELAY_PIN_MAPPING)] # Sort keys so order is the same

# connect and retrieve queue name
sqs = boto3.resource('sqs')
queue = sqs.get_queue_by_name(QueueName='garage-responses')

def setup_pins():
    GPIO.setmode(GPIO.BCM)
    for one_pin in RELAY_PIN_MAPPING.values():
        GPIO.setup(one_pin, GPIO.OUT)

    for one_pin in GARAGE_SENSOR_MAPPING.values():
        GPIO.setup(one_pin, GPIO.IN)

def get_garage_status(garage_name):
    error = True # Start by default with error
    try:
        pin_result = GPIO.input(GARAGE_SENSOR_MAPPING[garage_name])
    except KeyError:
        garage_status = 'INVALID GARAGE NAME'
    else:
        if pin_result == 0:
            garage_status = 'CLOSED'
            error = False
        elif pin_result == 1:
            garage_status = 'OPEN'
            error = False
        else:
            garage_status = 'UNKNOWN'

    return garage_status, error

def control_garage(garage_name, action):
    # action is (OPEN, CLOSE)
    action_error = True
    if garage_name not in RELAY_PIN_MAPPING:
        message = 'INVALID GARAGE_NAME'
        return message, action_error

    if action not in ('OPEN', 'CLOSE'):
        message = 'INVALID ACTION'
        return message, action_error

    # Check what the current location is
    current_garage_status, status_error = get_garage_status(garage_name)
    if current_garage_status == 'OPEN' and action == 'OPEN':
        message = 'Trying to open garage that is already open'
    elif current_garage_status == 'CLOSED' and action == 'CLOSE':
        message = 'Trying to close garage that is already closed'
    else:
        relay_pin = RELAY_PIN_MAPPING[garage_name]
        try:
#           GPIO.output(relay_pin,GPIO.HIGH)
            time.sleep(0.5)
#           GPIO.output(relay_pin,GPIO.LOW)
        except:
            message = 'AN ERROR OCCURED WHILE TRIGGERING THE RELAY'
        else:
            action_error = False
            message = 'TRIGGERED {0} GARAGE TO {1}. OLD POSITION: {2}'.format(garage_name, action, current_garage_status)

    # we dont return this in the output as it makes the message big
    if action_error:
        print(message)

    return message, action_error

def get_garage_json_status(garage_name, limit_keys=None):
    # limit_keys used to filter dictionary to trim down response
    response = []
    if garage_name.lower() == 'all':
        garage_name = SORTED_KEYS
    else:
        garage_name = [garage_name]

    for one_garage in garage_name:
        one_response = {}
        garage_status, error = get_garage_status(one_garage)

        # Nagios fields
        one_response['plugin_output'] = "Garage is {0}".format(garage_status)
        one_response['service_description'] = "{0} Garage Status".format(one_garage.capitalize())
        one_response['hostname'] = hostname
        one_response['return_code'] = "0" if garage_status == "CLOSED" else "2"

        one_response['garage_name'] = one_garage
        one_response['status_time'] = datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        one_response['status'] = garage_status
        one_response['error'] = error

        one_response = one_response if limit_keys is None else {k: one_response[k] for k in limit_keys if k in one_response}

        response.append(one_response)

    return json.dumps(response)

def garage_control_json(garage_name, current_status, limit_keys=None):
    response = {}
    response['status_time'] = datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

    message, error = control_garage(garage_name, current_status)

    response.update({'status': message, 'error': error})
    response = response if limit_keys is None else {k: response[k] for k in limit_keys if k in response}
    return json.dumps(response)

def process_sns_message(data):
    # message that came via SNS
    message_id = data['MessageId']
    raw_message = json.loads(data['Message'])
    action_type = raw_message['type']
    garage_name = raw_message['garage_name']

    #TODO figure out a better way to update the json
    if action_type == 'STATUS':
        response_keys = ['garage_name', 'status', 'error']
        status_list = json.loads(get_garage_json_status(garage_name, limit_keys=response_keys))
        return_message = {'status' : status_list}
    elif action_type == 'CONTROL':
        response_keys = ['error']
        current_status = raw_message['current_status']
        return_message = json.loads(garage_control_json(garage_name, current_status, limit_keys=response_keys))
        return_message['status'] = 'success' if not return_message['error'] else 'fail'
    else:
        return_message = {'status': 'Invalid action passed', 'error': True}
    return_message.update({'id': message_id[:4]})

    # publish the message to the queue
    print("TEST publishing {}".format(return_message))

#   queue.send_message(MessageBody=json.dumps(return_message))

# web related logic

@app.route('/garage/status/<garage_name>')
def garage_status_route(garage_name):
    return get_garage_json_status(garage_name)

@app.route('/sns-callback', methods=['POST'])
def sns_callback_route():
    try:
        data = json.loads(request.data.decode('utf-8'))
    except Exception as e:
        print(e)
        print("exception parsing {}".format(request.data))
    else:
        if data['Type'] == 'SubscriptionConfirmation' and 'SubscribeURL' in data:
            # call the subscription url to confirm
            print(data['SubscribeURL'])
            requests.get(data['SubscribeURL'])
        elif data['Type'] == 'Notification':
            # extract out the message and process
            print("Message is {}".format(data))
            process_sns_message(data)
        else:
            print("Couldnt process message: {}".format(data))

    return 'OK\n'


if __name__ == '__main__':
    try:
        setup_pins()
        port_number = int(config.get('general', 'port'))
        app.run(host='0.0.0.0', port=port_number)
    finally:
        GPIO.cleanup()
