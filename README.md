<H2>Logging AWS support cases from CloudWatch Alarms</H2>

Many customers are aware that they can contact AWS support through the traditional channels of web, phone and chat. However for customers on business or enterprise support, it’s also possible to interact directly with AWS support via API. 

Traditionally this type of integration has been used to integrate customer and supplier case management systems to hand over cases raised against customers system. However there is another way in which you can leverage a combination of AWS services to be able to automatically raise support cases to AWS based on alarms generated by external services, such as Amazon CloudWatch. 

Alarms generated by Amazon CloudWatch generate an Amazon SNS messages, this normally translate into an email but it’s also possible to forward this message into an Amazon SQS queue. With a simple application designed to read the Amazon SQS queue and appropriate case logging logic it is possible to then programatically raise a support case.

The reality is though for many non-developer customers starting on the platform is that being able to put these services together and write an application to orchestrate this process is quite daunting. However leveraging the AWS SDKs, a high level language such as Python and Elastic Beanstalk it’s possible to develop this very quickly. 

In order to demonstrate this I’ve provided a sample application which can be deployed into the Elastic Beanstalk as part of the architecture below:

<IMG SRC="https://github.com/mjs2180/eb-cw-support-api/blob/master/architecture.png">

In this example alarms are generated from Amazon CloudWatch, these can be created against resources in your AWS account or leverage services such as Amazon Route53 health checks. Messages are delivered into the Amazon SQS queue from Amazon CloudWatch via Amazon SNS. The actual application runs inside an AWS Elastic Beanstalk worker tier and consumes messages from the Amazon SQS queue. 

The message format which the application uses to raise the case is based on that produced by Amazon CloudWatch alarms, however there are only three key data elements that need to be present in order to log a case, as follows:

<pre><code>{
	"AlarmName":"My Alarm",
	"AlarmDescription":"More detailed description",
	"StateChangeTime":"Alarm Time"
}</code></pre>

This means that you can integrate any 3rd party monitoring system to make use of this interface, as long as it has the ability to write a message in the above format to Amazon SQS. The message is parsed by the application and a support case raised with the alarm name as the subject, priority is set to low in the current code but can be modified.

In order to make the system more extensible, configuration information regarding different alarms can also be stored in Amazon DynamoDB; this information is retrieved and then used to customise the support case when it's raised, including the priority and additional information to help the support team start working on the case.

The Amazon DynamoDB table must consist of the following attributes:

<pre><code>(hash)      : string    # Anything you want but the value must match the alarm name
priority    : string	# low, normal, high, urgent
action      : string	# JSON formated text to allow for custom message to be sent to support to help start troubleshooting
ccemail     : stringset # (optional) email address to cc when a case is raised</code></pre>

In order to implement the application there are a few steps that are required as follows:

<ol>
<li>Create IAM role for EC2 instance to be able to access required AWS services, the policy is included in the <a href="https://github.com/mjs2180/eb-cw-support-api/blob/master/eb-cw-support-worker-iam-policy.json">eb-cw-support-worker-iam-policy.json</a> file
(http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)</li> 
<li>Create an Amazon DynamoDB table with the required data elements for each alarm, please note that the read/write IOPS required are very low (http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GettingStartedDynamoDB.html)</li>	
<li>Deploy application to Elastic Beanstalk worker tier (http://docs.aws.amazon.com/elasticbeanstalk/latest/dg/GettingStarted.html)
Configure the following settings:</li>
<ol type="a">
<li>Application path should be set to "/serviceme"</li>
<li>DBREGION environment variable set to reflect AWS region where the DynamoDB is (default: us-east-1)</li>
<li>DBTABLE environment variable set to reflect the table name to query (default: cw-support-api)</li>
</ol>
<li>Create an Amazon SNS topic (http://docs.aws.amazon.com/sns/latest/dg/CreateTopic.html) and send messages to the SQS queue created by Elastic Beanstalk (http://docs.aws.amazon.com/sns/latest/dg/SendMessageToSQS.html)</li>
<li>Subscribe your Amazon SQS queue to the SNS topic (http://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqssubscribe.html)</li>
<li>Setup up your Amazon CloudWatch alarms and send notifications via the SNS topic (http://docs.aws.amazon.com/AmazonCloudWatch/latest/DeveloperGuide/ConsoleAlarms.html)</li>
<li>Sit back relax and wait for your cases to be automatically raised</li>
</ol>

One final big caveat I want you to think about though is making sure that you only raise alarms when you are really sure there is an issue you can't deal with through automation, which can also be driven by CloudWatch alarms; make sure that you're really dealing with an AWS issue before you raise cases, otherwise there isn't much AWS support will be able to help you with.