
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

HOST = "search-dining-concierge-roqnd4dgbwcixeiatvzafaxwum.us-east-1.es.amazonaws.com"
REGION = "us-east-1"
INDEX_NAME = "restaurants"

credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, REGION, "es")

client = OpenSearch(
    hosts=[{"host": HOST, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)

mapping = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0
    },
    "mappings": {
        "properties": {
            "RestaurantID": {"type": "keyword"},
            "Cuisine": {"type": "keyword"}
        }
    }
}

if client.indices.exists(index=INDEX_NAME):
    print("Index already exists:", INDEX_NAME)
else:
    response = client.indices.create(
        index=INDEX_NAME,
        body=mapping
    )
    print("Index created:", response)
