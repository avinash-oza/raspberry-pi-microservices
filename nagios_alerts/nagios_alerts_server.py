# coding: utf-8
import os
import sqlite3
import argparse
import datetime
import time
import mysql.connector
import ConfigParser
import json
from bottle import route, run, template, auth_basic, post, request, get

config = ConfigParser.ConfigParser()
config.read('nagios_alerts.config')

MESSAGE_TEXT="""
***** Nagios *****
Notification Type: {alert_type}
{host_or_service_line}
State: {host_state}
Address: {host_address}
Info: {output_text}

Date/Time: {n_datetime}
"""

@post('/send_nagios_alert')
def send_nagios_alert():
    print(request.json)
    data = request.json
    data['host_or_service_line'] = ""
    if data['alert_type'] == 'HOST':
        data['host_or_service_line'] = "HOST:{0}".format(data['host_name'])

    insert_alert(MESSAGE_TEXT.format(**data), data)

@route('/get_nagios_unsent_alerts')
def get_alerts():
     # Open the database
     db_host_name = config.get('DATABASE', 'host')
     db_user_name = config.get('DATABASE', 'user')
     db_password = config.get('DATABASE', 'password')
     database_name = config.get('DATABASE', 'database')

     conn =  mysql.connector.connect(user=db_user_name,password=db_password,host=db_host_name, database=database_name)
     cursor = conn.cursor(buffered=True)
     c = conn.cursor(buffered=True)
     write_cursor = conn.cursor(buffered=True)
     # Get the current unsent alerts. Make sure to send them in order
     c.execute("SELECT id date_inserted,date_sent,message_text,status,hostname,service_name, notification_type FROM nagios_alerts WHERE STATUS='UNSENT' ORDER BY id ASC LIMIT 5")
     # Enumerate the counter so we know how many results returned
     results = [one_result for one_result in c]
     total_count_of_alerts = len(results)

     ret = []

     for o in results:
         o = list(o)
         o[1] = o[1].strftime('%Y-%m-%d %H:%M:%S%p') if o[1] else o[1] # date inserted
         ret.append(o)

     return json.dumps(ret)


def insert_alert(alert_text, data):
    db_host_name = config.get('DATABASE', 'host')
    db_user_name = config.get('DATABASE', 'user')
    db_password = config.get('DATABASE', 'password')
    database_name = config.get('DATABASE', 'database')

    conn = mysql.connector.connect(user=db_user_name,password=db_password,host=db_host_name, database=database_name)
    cursor = conn.cursor(buffered=True)

    query =  """INSERT INTO `nagios_alerts`(`message_text`, `hostname`, `service_name`, `notification_type`) VALUES ("{0}", "{1}", "{2}", "{3}")""".format(alert_text, data['host_name'], data['service_name'], data['notification_type'])
    print query
    cursor.execute(query )
    # Commit the changes
    conn.commit()
    conn.close()

@route('/acknowledge/<alert_id>')
def acknowledge_alert(alert_id):
     db_host_name = config.get('DATABASE', 'host')
     db_user_name = config.get('DATABASE', 'user')
     db_password = config.get('DATABASE', 'password')
     database_name = config.get('DATABASE', 'database')

     conn =  mysql.connector.connect(user=db_user_name,password=db_password,host=db_host_name, database=database_name)
     cursor = conn.cursor(buffered=True)
     # Get the current unsent alerts. Make sure to send them in order
     query = "SELECT hostname, service_name FROM nagios_alerts where id=%s"
     cursor.execute(query, (alert_id,))

     results = [c for c in cursor]
     if not results:
         return "No results found for id {0}".format(alert_id)

     host_name, service_name = results[0]

     # alert id was found, construct string to write for downtime and commenting
     current_time = int(time.time())
     svc_comment_string = "[{timestamp}] ADD_SVC_COMMENT;{host_name};{service_name};0;web_service;DOWNTIME SCHEDULED VIA TELEGRAM".format(timestamp=current_time,
                                                                                                                                       host_name=host_name,
                                                                                                                                       service_name=service_name)

     one_day = 60*60*24 # 24 hours
     downtime_string = "[{timestamp}] SCHEDULE_SVC_DOWNTIME;{host_name};{service_name};{timestamp};{end_time};1;0;{one_day};web_service;DOWNTIME SCHEDULED VIA TELEGRAM".format(timestamp=current_time,
                                                                                                                                       host_name=host_name,
                                                                                                                                       service_name=service_name,
                                                                                                                                       one_day=one_day,
                                                                                                                                       end_time=current_time + one_day)
     lines_to_write = [downtime_string, svc_comment_string]
     with open('/var/lib/nagios3/rw/nagios.cmd','a') as f:
         for one_line in lines_to_write:
             f.write(one_line + '\n')

     return "Success"


port_number = int(config.get('general', 'port'))
run(host='0.0.0.0', port=port_number)

