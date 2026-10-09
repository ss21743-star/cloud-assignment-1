
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, helpers

REGION = "us-east-1"
HOST = "search-dining-concierge-roqnd4dgbwcixeiatvzafaxwum.us-east-1.es.amazonaws.com"
TABLE_NAME = "yelp-restaurants"
INDEX_NAME = "restaurants"

session = boto3.Session(region_name=REGION)
credentials = session.get_credentials()
auth = AWSV4SignerAuth(credentials, REGION, "es")

client = OpenSearch(
    hosts=[{"host": HOST, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=60
)

dynamodb = session.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

print("Reading restaurants from DynamoDB...")

restaurants = []
scan_kwargs = {
    "ProjectionExpression": "BusinessID, Cuisine"
}

while True:
    response = table.scan(**scan_kwargs)
    restaurants.extend(response.get("Items", []))

    if "LastEvaluatedKey" not in response:
        break

    scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

print(f"Found {len(restaurants)} restaurants.")

actions = []

for restaurant in restaurants:
    actions.append({
        "_index": INDEX_NAME,
        "_id": restaurant["BusinessID"],
        "_source": {
            "RestaurantID": restaurant["BusinessID"],
            "Cuisine": restaurant["Cuisine"],
            "DocumentType": "Restaurant"
        }
    })

print("Uploading restaurants to OpenSearch...")

success, errors = helpers.bulk(
    client,
    actions,
    chunk_size=100,
    raise_on_error=False
)

print(f"Successfully indexed: {success}")
print(f"Failed: {len(errors)}")

if errors:
    print("First error:", errors[0])

client.indices.refresh(index=INDEX_NAME)

count = client.count(index=INDEX_NAME)["count"]
print(f"Total restaurants in OpenSearch: {count}")

# Verify that the documents have the Restaurant document type
verification = client.count(
    index=INDEX_NAME,
    body={
        "query": {
            "term": {
                "DocumentType.keyword": "Restaurant"
            }
        }
    }
)

print(f"Documents with Restaurant type: {verification['count']}")
