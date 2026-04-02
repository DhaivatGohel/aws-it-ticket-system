import json
import boto3
import uuid
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb', region_name='ca-central-1')
table = dynamodb.Table('it-tickets')

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
    else:
        return 'General'

def prioritize(description, category):
    text = description.lower()
    if any(word in text for word in ['urgent', 'critical', 'down', 'outage', 'emergency', 'breach']):
        return 'Critical'
    elif any(word in text for word in ['slow', 'not working', 'broken', 'failed', 'cant access', "can't access"]):
        return 'High'
    elif category in ['Network', 'Access']:
        return 'Medium'
    else:
        return 'Low'

def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': ''
        }

    try:
        body = json.loads(event.get('body', '{}'))
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

        table.put_item(Item=ticket)

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

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Internal server error'})
        }