"""Lex V2 validation, conversation responses, and recommendation reuse."""

import json
import re
import uuid
from datetime import datetime, date
from zoneinfo import ZoneInfo
import boto3

REGION = 'us-east-1'
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/855997689930/Q1'

sqs = boto3.client('sqs', region_name=REGION)
state_table = boto3.resource('dynamodb', region_name=REGION).Table(
    'dining-search-state'
)

CUISINES = ['Chinese', 'Japanese', 'Indian', 'Italian', 'Mexican']

ORDER = [
    'Location',
    'Cuisine',
    'NumberOfPeople',
    'DiningTime',
    'DiningHour',
    'Email'
]

PROMPTS = {
    'Location': 'Great. What city or city area are you looking to dine in?',
    'Cuisine': 'Got it, Manhattan. What cuisine would you like to try? Chinese, Japanese, Indian, Italian, or Mexican?',
    'NumberOfPeople': 'How many people are in your party?',
    'DiningTime': 'What date would you like to dine?',
    'DiningHour': 'What time would you like to dine?',
    'Email': 'Lastly, what email address should I send your suggestions to?'
}


def lambda_handler(event, context):
    state = event.get('sessionState') or {}
    intent = state.get('intent') or {}
    name = intent.get('name', 'FallbackIntent')
    slots = intent.get('slots') or {}
    attrs = dict(state.get('sessionAttributes') or {})

    def reply(action, text, status='InProgress', slot=None):
        dialog = {'type': action}

        if slot:
            dialog['slotToElicit'] = slot

        return {
            'sessionState': {
                'sessionAttributes': attrs,
                'dialogAction': dialog,
                'intent': {
                    'name': name,
                    'slots': slots,
                    'state': status
                }
            },
            'messages': [
                {
                    'contentType': 'PlainText',
                    'content': text
                }
            ]
        }

    # GreetingIntent
    if name == 'GreetingIntent':
        attrs.clear()
        return reply(
            'Close',
            'Hi there, how can I help?',
            'Fulfilled'
        )

    # ThankYouIntent
    if name == 'ThankYouIntent':
        return reply(
            'Close',
            "You're welcome! Enjoy your meal.",
            'Fulfilled'
        )

    # FallbackIntent
    if name != 'DiningSuggestionsIntent':
        return reply(
            'Close',
            'I can help with restaurant suggestions in Manhattan. Say "I need restaurant suggestions" to begin.',
            'Fulfilled'
        )

    def value(key):
        return (
            ((slots.get(key) or {}).get('value') or {})
            .get('interpretedValue')
        )

    def invalid(key, text):
        slots[key] = None
        return reply('ElicitSlot', text, slot=key)

    now = datetime.now(ZoneInfo('America/New_York'))
    values = {key: value(key) for key in ORDER}

    # Validate location
    if values['Location']:
        entered_location = values['Location'].strip()

        if entered_location.lower() not in [
            'manhattan',
            'new york',
            'new york city',
            'nyc'
        ]:
            return invalid(
                'Location',
                f"Sorry, I can't fulfill requests for {entered_location}. Please enter a valid location."
            )

        values['Location'] = 'Manhattan'

    # Validate cuisine
    if values['Cuisine']:
        cuisine = values['Cuisine'].strip().title()

        if cuisine not in CUISINES:
            return invalid(
                'Cuisine',
                'Please choose Chinese, Japanese, Indian, Italian, or Mexican.'
            )

        values['Cuisine'] = cuisine

    # Validate party size
    if values['NumberOfPeople']:
        try:
            party = int(values['NumberOfPeople'])

            if party < 1 or party > 20:
                raise ValueError()

        except (ValueError, TypeError):
            return invalid(
                'NumberOfPeople',
                'Please enter a whole number from 1 to 20 for your party size.'
            )

    # Validate dining date
    if values['DiningTime']:
        try:
            day = date.fromisoformat(values['DiningTime'])

            if day < now.date():
                raise ValueError()

        except (ValueError, TypeError):
            return invalid(
                'DiningTime',
                'Please choose today or a future date.'
            )

    # Validate dining time
    if values['DiningHour']:
        try:
            hour = datetime.strptime(
                values['DiningHour'], '%H:%M'
            ).time()

        except (ValueError, TypeError):
            return invalid(
                'DiningHour',
                'Please enter a specific dining time, such as 7 pm.'
            )

        if (
            values['DiningTime']
            and datetime.combine(
                day, hour, tzinfo=now.tzinfo
            ) <= now
        ):
            return invalid(
                'DiningHour',
                'That time has already passed. Please choose a future time.'
            )

    # Validate email
    if values['Email'] and not re.fullmatch(
        r'[^\s@]+@[^\s@]+\.[^\s@]+',
        values['Email']
    ):
        return invalid(
            'Email',
            'Please enter a valid email address, such as ss21743@nyu.edu.'
        )

    # Ask for missing slots
    for key in ORDER:
        if not values[key]:

            if event.get('invocationLabel') == key:
                errors = {
                    'Location': "Sorry, I can't fulfill requests for that location. Please enter a valid location.",
                    'Cuisine': 'Please choose Chinese, Japanese, Indian, Italian, or Mexican.',
                    'Email': 'Please enter a valid email address, such as ss21743@nyu.edu.',
                    'NumberOfPeople': 'Please enter a whole number from 1 to 20.',
                    'DiningTime': 'Please enter today or a future date.',
                    'DiningHour': 'Please enter a specific future time, such as 7 pm.'
                }

                return reply(
                    'ElicitSlot',
                    errors[key],
                    slot=key
                )

            return reply(
                'ElicitSlot',
                PROMPTS[key],
                slot=key
            )

    # Extra credit: Remember previous searches
    user_id = event['sessionId']

    previous = state_table.get_item(
        Key={'UserId': user_id},
        ConsistentRead=True
    ).get('Item') or {}

    same = (
        previous.get('Location') == values['Location']
        and previous.get('Cuisine') == values['Cuisine']
        and previous.get('RestaurantIDs')
    )

    request = dict(
        values,
        UserId=user_id,
        RequestId=str(uuid.uuid4())
    )

    if same and attrs.get('reuseAsked') != 'yes':
        attrs['reuseAsked'] = 'yes'

        return reply(
            'ConfirmIntent',
            'You searched for this location and cuisine before. Would you like the same restaurant recommendations as last time?'
        )

    if same and attrs.get('reuseAsked') == 'yes':
        confirmation = intent.get('confirmationState')

        if confirmation == 'Confirmed':
            request['RestaurantIDs'] = previous['RestaurantIDs']

        elif confirmation != 'Denied':
            return reply(
                'ConfirmIntent',
                'Would you like the same recommendations? Please say yes or no.'
            )

    # Send request to SQS
    try:
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(request)
        )

    except Exception:
        return reply(
            'Close',
            'Sorry, I could not submit your request. Please try again.',
            'Failed'
        )

    attrs.pop('reuseAsked', None)

    return reply(
        'Close',
        'You are all set! I received your request and will email your restaurant suggestions shortly. Have a good day!',
        'Fulfilled'
    )
