
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

HOST = "search-dining-concierge-roqnd4dgbwcixeiatvzafaxwum.us-east-1.es.amazonaws.com"
REGION = "us-east-1"

credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, REGION, "es")

client = OpenSearch(
    hosts=[{"host": HOST, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)

try:
    print("Connecting to OpenSearch...")
    print(client.info())
    print("Connection successful!")
except Exception as error:
    print("Connection failed:", error)

response = client.search(
    index="restaurants",
    body={
        "size": 3,
        "query": {
            "term": {
                "Cuisine": "Italian"
            }
        }
    }
)

print("\nItalian restaurant search results:")

for hit in response["hits"]["hits"]:
    print(hit["_source"])
