import json
import boto3
import uuid
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb', region_name='ca-central-1')
table = dynamodb.Table('it-tickets')

# SES client for sending emails
ses = boto3.client('ses', region_name='ca-central-1')

# The email address that sends AND receives alerts
# Both must be verified in SES while in sandbox mode
ALERT_EMAIL = 'dhaivatgohel01@outlook.com'

def categorize(description):
    text = description.lower()
    if any(word in text for word in ['laptop', 'computer', 'printer', 'monitor', 'keyboard', 'mouse', 'hardware']):
        return 'Hardware'
    elif any(word in text for word in ['network', 'wifi', 'internet', 'vpn', 'connection', 'ethernet']):
        return 'Network'
    elif any(word in text for word in ['password', 'login', 'access', 'account', 'locked', 'permission']):
        return 'Access'
    elif any(word in text for word in ['software', 'app', 'install', 'crash', 'error', 'update', 'virus']):
        return 'Software'
    elif any(word in text for word in ['phishing', 'email', 'spam', 'suspicious', 'malware']):
        return 'Security'
    elif any(word in text for word in ['teams', 'outlook', 'office', 'microsoft', 'onedrive', 'sharepoint']):
        return 'Software'
    elif any(word in text for word in ['intune', 'mfa', 'authenticator', 'vpn', 'azure', 'entra']):
        return 'Access'
    else:
        return 'General'

def prioritize(description, category):
    text = description.lower()
    if any(word in text for word in ['urgent', 'critical', 'down', 'outage', 'emergency', 'breach', 'ransomware', 'hacked']):
        return 'Critical'
    elif any(word in text for word in ['slow', 'not working', 'broken', 'failed', 'cant access', "can't access", 'unable', 'keeps crashing']):
        return 'High'
    elif category in ['Network', 'Access', 'Security']:
        return 'Medium'
    else:
        return 'Low'

def send_alert_email(ticket):
    """
    Sends an email notification to the IT team when a new ticket is submitted.
    Uses SES to deliver the email.
    """

    # Priority emoji for quick visual scanning
    priority_emoji = {
        'Critical': 'CRITICAL',
        'High':     'HIGH',
        'Medium':   'MEDIUM',
        'Low':      'LOW'
    }

    priority_label = priority_emoji.get(ticket['priority'], ticket['priority'])

    subject = f"[{priority_label}] New IT Ticket — {ticket['category']} issue from {ticket['name']}"

    body = f"""New IT support ticket submitted.

Ticket ID:   {ticket['ticketId']}
Submitted:   {ticket['createdAt']}

From:        {ticket['name']}
Email:       {ticket['email']}
Category:    {ticket['category']}
Priority:    {ticket['priority']}
Status:      {ticket['status']}

Description:
{ticket['description']}

---
View all tickets: https://d23mh63awvqncl.cloudfront.net/dashboard.html
AWS IT Ticket Triage System — ca-central-1
"""

    try:
        ses.send_email(
            Source=ALERT_EMAIL,
            Destination={'ToAddresses': [ALERT_EMAIL]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body':    {'Text': {'Data': body, 'Charset': 'UTF-8'}}
            }
        )
        print(f"Alert email sent for ticket {ticket['ticketId']}")
    except Exception as e:
        # Email failure should not block ticket submission
        # Log the error but continue
        print(f"Email send failed: {str(e)}")

def get_all_tickets():
    response = table.scan()
    tickets = response.get('Items', [])
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps({'tickets': tickets})
    }

def create_ticket(body):
    name        = body.get('name', 'Anonymous')
    email       = body.get('email', '')
    description = body.get('description', '')

    if not description:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Description is required'})
        }

    category = categorize(description)
    priority = prioritize(description, category)

    ticket = {
        'ticketId':    str(uuid.uuid4()),
        'name':        name,
        'email':       email,
        'description': description,
        'category':    category,
        'priority':    priority,
        'status':      'Open',
        'createdAt':   datetime.now(timezone.utc).isoformat()
    }

    # Save to DynamoDB first — if this fails, we want to know immediately
    table.put_item(Item=ticket)

    # Send email alert — failure here does not block the response
    send_alert_email(ticket)

    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({
            'message':  'Ticket submitted successfully',
            'ticketId': ticket['ticketId'],
            'category': category,
            'priority': priority
        })
    }

def lambda_handler(event, context):
    method = event.get('httpMethod', '')
    params = event.get('queryStringParameters') or {}

    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': ''
        }

    try:
        if method == 'GET' and params.get('action') == 'list':
            return get_all_tickets()

        if method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return create_ticket(body)

        return {
            'statusCode': 405,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'})
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Internal server error'})
        }