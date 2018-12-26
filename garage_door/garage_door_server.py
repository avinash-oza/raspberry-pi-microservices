import time
import datetime
import json
import configparser
import requests

from flask import Flask, request
from flask_restplus import Api, Resource, fields, marshal
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
    response = {'garage_name': garage_name, 'error': True}

    if garage_name not in RELAY_PIN_MAPPING:
        response['message'] = 'INVALID GARAGE_NAME'
        return response

    if action not in ('OPEN', 'CLOSE'):
        response['message'] = 'INVALID ACTION'
        return response

    # Check what the current location is
    current_garage_status, status_error = get_garage_status(garage_name)
    if current_garage_status == 'OPEN' and action == 'OPEN':
        response['message'] = 'Trying to open garage that is already open'
    elif current_garage_status == 'CLOSED' and action == 'CLOSE':
        response['message'] = 'Trying to close garage that is already closed'
    else:
        relay_pin = RELAY_PIN_MAPPING[garage_name]
        try:
#           GPIO.output(relay_pin,GPIO.HIGH)
            time.sleep(0.5)
#           GPIO.output(relay_pin,GPIO.LOW)
        except:
            response['message'] = 'AN ERROR OCCURED WHILE TRIGGERING THE RELAY'
        else:
            response['error'] = False
            response['message'] = 'TRIGGERED {0} GARAGE TO {1}. OLD POSITION: {2}'.format(garage_name, action, current_garage_status)

    return response

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

# web related logic

GarageStatusModel = api.model('GarageStatusModel', {
    'garage_name': fields.String(),
    'status': fields.String(),
    'error': fields.Boolean(),
    'message': fields.String(allow_null=True)
})

NagiosGarageStatusModel = api.inherit('NagiosGarageStatusModel', GarageStatusModel,
                                      {'return_code': fields.String(),
                                       'plugin_output': fields.String(),
                                       'status_time': fields.String(),
                                       'service_description': fields.String()
                                       }
                                      )

GarageStatusResponseModel = api.model('GarageStatusResponseModel',
                                      {'status': fields.List(fields.Nested(GarageStatusModel)),
                                       'type': fields.String(default='STATUS'),
                                        'id': fields.String()
                                       }
                                      )


@api.route('/garage/status')
class GarageStatusResource(Resource):
    @api.marshal_with(GarageStatusResponseModel)
    def get(self, garage_name='ALL'):
        return {'status': get_garage_json_status(garage_name), 'type': 'STATUS' }


#TODO: Maybe a better way to keep track of this
class MessageType(fields.Raw):
    def format(self, value):
        return value.upper() if value.upper() in ('STATUS', 'CONTROL') else None

class ActionType(fields.Raw):
    def format(self, value):
        return value.upper() if value.upper() in ('OPEN', 'CLOSE') else None

class GarageNameType(fields.Raw):
    def format(self, value):
        return value.upper() if value.upper() in ('LEFT', 'RIGHT') else None


SNSMessageModel = api.model('SNSMessageModel', {
    'type': MessageType,
    'action': ActionType,
    'garage_name': GarageNameType
})


@api.route('/sns-callback')
class SNSCallbackResource(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, *args, **kwargs)
        #TODO: queue name from config
        sqs = boto3.resource('sqs')
        self._queue = sqs.get_queue_by_name(QueueName='garage-responses')

    def post(self):
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
                self.process_sns_message(data)
            else:
                print("Couldnt process message: {}".format(data))

        return 'OK\n'

    def process_sns_message(self, data):
        # message that came via SNS
        message_id = data['MessageId']
        raw_input_message = json.loads(data['Message']) # the message as it was sent in
        cleaned_message = marshal(raw_input_message, SNSMessageModel)
        action_type = cleaned_message['type']
        garage_name = cleaned_message['garage_name']

        response = {'id': message_id[:4], 'type': 'STATUS'}

        if action_type == 'STATUS':
            response['status'] = get_garage_json_status(garage_name, limit_keys=response_keys)
        elif action_type == 'CONTROL':
            response['status'] = [control_garage(garage_name, action_type)]
        else:
            response['status'] = [{'message': 'Invalid action passed', 'error': True}]

        # publish the message to the queue
        print("TEST publishing {}".format(response))

        # self._queue.send_message(MessageBody=json.dumps(response))


if __name__ == '__main__':
    try:
        setup_pins()
        port_number = int(config.get('general', 'port'))
        app.run(host='0.0.0.0', port=port_number)
    finally:
        GPIO.cleanup()
