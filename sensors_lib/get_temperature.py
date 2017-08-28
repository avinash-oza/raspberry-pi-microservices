import sys
import re
import ConfigParser
import time
import argparse
import subprocess

def get_ds18b20_sensor(sensor_id, critical_temp):
    command_to_run="""cat /sys/bus/w1/devices/{0}/w1_slave""".format(sensor_id)
    output = subprocess.check_output([command_to_run], shell=True)
    filter_string = 't=(\d+)'
    found_matches = re.search(filter_string, output)
    temperature = output.rsplit('=', 1)[1].strip()

    # Convert temperature to F
    f_degrees = 1.8*float(temperature)/1000 + 32
    error_code = 0
    if f_degrees > CRITICAL_TEMP:
        error_code = 2

    return f_degrees, error_code

if __name__ == '__main__':
    get_ds18b20_sensor('28-05167155beff')

