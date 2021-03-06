import time
import ConfigParser
from bottle import get, post, request, run

config = ConfigParser.RawConfigParser()
config.read('nagios_passive_check.config')

@post('/submit_nagios_command')
def submit_nagios_command():
    # Takes the input text and writes it out to nagios.cmd
    line_to_write = request.body.read()
    with open('/var/lib/nagios3/rw/nagios.cmd', 'a') as f:
        f.write(line_to_write + '\n')
    return

@get('/submit_check')
def login():
    return '''
            <form action="/submit_check" method="post">
                        Username: <input name="hostname" type="text" />
                        Username: <input name="service_description" type="text" />
                        Username: <input name="return_code" type="text" />
                        Username: <input name="plugin_output" type="text" />
                                                <input value="Login" type="submit" />
                                                        </form>
                                                            '''
@post('/submit_check')
def do_login():
    # Response should always be a list of json dicts
    lines_to_write = []
    for one_item in request.json:
        current_timestamp = int(time.time())
        hostname = one_item.get('hostname')
        service_description = one_item.get('service_description')
        return_code = one_item.get('return_code')
        service_output = one_item.get('plugin_output')

        lines_to_write.append('[{0}] {1}'.format(current_timestamp, ';'.join(['PROCESS_SERVICE_CHECK_RESULT', hostname, service_description, return_code, service_output])))

    with open('/var/lib/nagios3/rw/nagios.cmd', 'a') as f:
        for l in lines_to_write:
            f.write(l + '\n')
    return

port_number = int(config.get('general', 'port'))
run(host='0.0.0.0', port=port_number)
