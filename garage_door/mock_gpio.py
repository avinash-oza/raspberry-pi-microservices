from unittest import mock
GPIO = mock.Mock()
def return_func(arg):
    print(arg)
    # simulate LEFT OPEN right closed
    # GARAGE_SENSOR_MAPPING = {'LEFT': 25, 'RIGHT': 16}
    return 1 if arg == 25 else 0
GPIO.input.side_effect = return_func

# @api.route('/sns-callback-test')
# class SNSTestResource(SNSCallbackResource):
#     def get(self):
#         data = {'MessageId': '123', 'Message': json.dumps({'type': 'STATUS', 'action': None, 'garage_name': 'ALL'})}
#         self.process_sns_message(data)