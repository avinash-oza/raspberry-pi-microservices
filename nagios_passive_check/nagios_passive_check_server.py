import time
import ConfigParser
from bottle import get, post, request, run

config = ConfigParser.RawConfigParser()
config.read('nagios_passive_check.config')

#get('/login')
#ef login():
#   return '''
#           <form action="/submit_check" method="post">
#                       Username: <input name="hostname" type="text" />
#                       Username: <input name="service_description" type="text" />
#                       Username: <input name="return_code" type="text" />
#                       Username: <input name="plugin_output" type="text" />
#                                               <input value="Login" type="submit" />
#                                                       </form>
#                                                           '''
@post('/submit_check')
def do_login():
    current_timestamp = int(time.time())
    hostname = request.forms.get('hostname')
    service_description = request.forms.get('service_description')
    return_code = request.forms.get('return_code')
    service_output = request.forms.get('plugin_output')

    line_to_write = '[{0}] {1}'.format(current_timestamp, ';'.join(['PROCESS_SERVICE_CHECK_RESULT', hostname, service_description, return_code, service_output]))

    with open('/var/lib/nagios3/rw/nagios.cmd', 'a') as f:
        f.write(line_to_write)

    return line_to_write

port_number = int(config.get('general', 'port'))
run(host='0.0.0.0', port=port_number)
