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

def get_all_tickets():
    # Scan returns all items in the table
    # In production you'd paginate this — scan returns max 1MB per call
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

def lambda_handler(event, context):
    method = event.get('httpMethod', '')
    params = event.get('queryStringParameters') or {}

    # CORS preflight
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
        # GET request with ?action=list — dashboard fetching all tickets
        if method == 'GET' and params.get('action') == 'list':
            return get_all_tickets()

        # POST request — new ticket submission
        if method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return create_ticket(body)

        # Anything else
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