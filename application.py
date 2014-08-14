# This software is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

# Description: Log support cases using AWS Support API based on Alarms from
# Amazon CloudWatch passed via Amazon SNS and Amazon SQS.
#
# Author: Mark Statham

import os
import logging
import json
import flask
from flask import request, Response

import boto
import boto.dynamodb

# Create and configure the Flask app
application = flask.Flask(__name__)
application.config.from_object('default_config')
application.debug = application.config['FLASK_DEBUG'] in ['true', 'True']

# Email message vars
BODY = "Hi Support\n\nWe've detected an issue via an automated alarm, please investigate. Alarm details are below: \n\nAlarm Name: %s\nAlarm Description: %s\nEvent Time: %s\nAction Required:\n%s\n\nRaw Alarm Format\n%s"
BODY2 = "Hi Support\n\nIt's happened again! Please investigate. Alarm details are below: \n\nAlarm Name: %s\nAlarm Description: %s\nEvent Time: %s\nAction Required:\n%s\n\nRaw Alarm Format\n%s"

@application.route('/serviceme', methods=['POST'])


def serviceme():
        """Log or Update a support case"""

        response = None
        if request.json is None:
                # Expect application/json request
                response = Response("", status=415)
        else:
                message = dict()
                try:
                # If the message has an SNS envelope, extract the inner message
                        if request.json.has_key('TopicArn') and request.json.has_key('Message'):
                                message = json.loads(request.json['Message'])
                        else:
                                message = request.json

                        # Connect to CloudWatch API in default region
                        cloudwatch = boto.connect_cloudwatch()

                        # Conenct to the support API in default region
                        support = boto.connect_support()

                        # Connect to dynamoDB in specified region
                        try:
                            print os.environ['DBREGION']
                        except KeyError:
                            # Connect to default region
                            ddb = boto.dynamodb.connect_to_region('us-east-1')
                        else:
                            # Connect to specified region
                            ddb = boto.dynamodb.connect_to_region(os.environ['DBREGION'])

                        # Set the DynamoDB table name
                        try:
                            print os.environ['DBTABLE']
                        except KeyError:
                            # Connect to default region
                            tablename = 'cw-support-api'
                        else:
                            # Connect to specified region
                            tablename = os.environ['DBTABLE']

                        # Open the DynamoDB table
                        try:
                            configtable = ddb.get_table(tablename)
                        except boto.dynamodb.exceptions.DynamoDBResponseError:
                            print 'cannot open the table %s' % tablename                        

                        try:
                            configitem = configtable.get_item(hash_key=message['AlarmName'])
                        except boto.dynamodb.exceptions.DynamoDBKeyNotFoundError:
                            # Set defaults
                            priority = 'low'
                            action = 'Please contact us for more information'
                        else:
                            # Get alarm specific configuration
                            priority = configitem['priority']
                            action = json.loads(configitem['action'])
                            try:
                                print configitem['ccemail']
                            except KeyError:
                                ccemail = None
                            else:
                                ccemail = configitem['ccemail']

                        # Get a list of open cases
                        cases = support.describe_cases()

                        # Check if one of the open matches the CloudWatch Alert Name
                        for x in range(len(cases['cases'])):
                                if (cases['cases'][x]['subject'] == (message['AlarmName'])):
                                        caseid = (cases['cases'][x]['caseId'])

                        # OK is there an existing case
                        try:
                                print caseid
                        except NameError:
                                # No existing case exists, lets open a new case
                                newcase = support.create_case(subject = (message['AlarmName']),
                                                              service_code='amazon-elastic-compute-cloud-linux',
                                                              category_code='other',
                                                              cc_email_addresses=ccemail,
                                                              communication_body=BODY % (message['AlarmName'],
                                                                                         message['AlarmDescription'],
                                                                                         message['StateChangeTime'],
                                                                                         json.dumps(action, indent=4, sort_keys=True),
                                                                                         json.dumps(message, indent=4, sort_keys=True)),
                                                                severity_code=priority)
                                response = Response("", status=200)
                                cloudwatch.put_metric_data('Support','Case/Logged',1,unit='Count')
                        else:
                                # There is an existing case, lets add some communication
                                result = support.add_communication_to_case(communication_body=BODY2 % (message['AlarmName'],
                                                                                                       message['AlarmDescription'],
                                                                                                       message['StateChangeTime'],
                                                                                                       json.dumps(action, indent=4, sort_keys=True),
                                                                                                       json.dumps(message, indent=4, sort_keys=True)),
                                                                           	case_id=caseid)
                                response = Response("", status=200)
                                cloudwatch.put_metric_data('Support','Case/Updated',1,unit='Count')
                except Exception as ex:
                        logging.exception('Error processing message: %s' % request.json)
                        response = Response(ex.message, status=500)

        return response

if __name__ == '__main__':
    application.run(host='0.0.0.0')
