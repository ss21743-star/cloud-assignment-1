import json
import os
import random
import boto3
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth
from botocore.httpsession import URLLib3Session

REGION = "us-east-1"
HOST = "https://search-dining-concierge-roqnd4dgbwcixeiatvzafaxwum.us-east-1.es.amazonaws.com"
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/855997689930/Q1"

SENDER_EMAIL = "ss21743@nyu.edu"
sqs = boto3.client("sqs", region_name=REGION)
ses = boto3.client("ses", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table("yelp-restaurants")
state_table = dynamodb.Table("dining-search-state")

def search_restaurants(cuisine):
    credentials = boto3.Session().get_credentials().get_frozen_credentials()

    query = {
        "size": 3,
        "query": {
            "function_score": {
                "query": {"term": {"Cuisine": cuisine.title()}},
                "random_score": {"seed": random.randrange(2147483647), "field": "_seq_no"},
                "boost_mode": "replace"
            }
        }
    }

    url = HOST + "/restaurants/_search"
    request = AWSRequest(
        method="POST",
        url=url,
        data=json.dumps(query).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    SigV4Auth(credentials, "es", REGION).add_auth(request)
    response = URLLib3Session().send(request.prepare())

    if response.status_code != 200:
        raise Exception(
            f"OpenSearch error {response.status_code}: "
            + response.content.decode("utf-8")
        )

    data = json.loads(response.content)
    hits = data["hits"]["hits"]

    random.shuffle(hits)
    return [hit["_source"]["RestaurantID"] for hit in hits[:3]]

def get_restaurant_details(restaurant_id):
    response = table.get_item(Key={"BusinessID": restaurant_id})
    return response.get("Item")

def send_email(recipient, cuisine, restaurants, request):
    lines = [
        f"Hello! Here are my {cuisine} restaurant suggestions for {request.get('NumberOfPeople', 'your party')} people, for {request.get('DiningTime', 'your selected date')} at {request.get('DiningHour', 'your selected time')}:",
        ""
    ]

    for i, restaurant in enumerate(restaurants, 1):
        lines.append(
            f"{i}. {restaurant.get('Name', 'Restaurant')}\n"
            f"Address: {restaurant.get('Address', 'Not available')}\n"
            f"Rating: {restaurant.get('Rating', 'N/A')}\n"
        )

    lines.append("\nEnjoy your meal!")

    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={"ToAddresses": [recipient]},
        Message={
            "Subject": {
                "Data": "Your Dining Concierge Recommendations"
            },
            "Body": {
                "Text": {
                    "Data": "\n".join(lines)
                }
            }
        }
    )

def lambda_handler(event, context):
    if event.get("action") == "inspect_index":
        credentials = boto3.Session().get_credentials().get_frozen_credentials()
        query = {"size": 1, "track_total_hits": True, "aggs": {"cuisines": {"terms": {"field": "Cuisine", "size": 20}}, "types": {"terms": {"field": "DocumentType.keyword", "size": 10}}}}
        request = AWSRequest(method="POST", url=HOST + "/restaurants/_search", data=json.dumps(query).encode(), headers={"Content-Type": "application/json"})
        SigV4Auth(credentials, "es", REGION).add_auth(request)
        response = URLLib3Session().send(request.prepare())
        if response.status_code != 200:
            raise RuntimeError("OpenSearch inspection failed: " + str(response.status_code))
        return json.loads(response.content)
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=5,
        WaitTimeSeconds=0,
        VisibilityTimeout=120
    )

    messages = response.get("Messages", [])

    if not messages:
        print("No messages in SQS.")
        return {"statusCode": 200, "body": "No messages"}

    processed = 0

    for message in messages:
        try:
            request = json.loads(message["Body"])

            cuisine = request["Cuisine"]
            email = request["Email"]

            restaurant_ids = request.get("RestaurantIDs") or search_restaurants(cuisine)

            restaurants = []
            for restaurant_id in restaurant_ids:
                details = get_restaurant_details(restaurant_id)
                if details:
                    restaurants.append(details)

            if not restaurants:
                raise Exception("No restaurant recommendations found")

            send_email(email, cuisine, restaurants, request)

            if request.get("UserId"):
                state_table.put_item(Item={
                    "UserId": request["UserId"],
                    "Location": request.get("Location", "Manhattan"),
                    "Cuisine": cuisine,
                    "RestaurantIDs": [r["BusinessID"] for r in restaurants],
                    "RequestId": request.get("RequestId", "")
                })

            sqs.delete_message(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=message["ReceiptHandle"]
            )

            processed += 1
            print(f"Recommendations sent for {cuisine}")

        except Exception as error:
            print(f"Failed to process request: {error}")
            # Leave message in SQS so it can be retried.

    return {
        "statusCode": 200,
        "body": f"Processed {processed} messages"
    }
