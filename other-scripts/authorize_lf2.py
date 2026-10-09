
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

HOST = "search-dining-concierge-roqnd4dgbwcixeiatvzafaxwum.us-east-1.es.amazonaws.com"
REGION = "us-east-1"

LF2_ROLE = "arn:aws:iam::855997689930:role/service-role/LF2-role-beaetj3a"

credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, REGION, "es")

client = OpenSearch(
    hosts=[{"host": HOST, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)

role_name = "lf2_restaurant_reader"

role = {
    "cluster_permissions": [],
    "index_permissions": [
        {
            "index_patterns": ["restaurants"],
            "allowed_actions": ["read"]
        }
    ],
    "tenant_permissions": []
}

print("Creating LF2 read-only role...")
print(client.transport.perform_request(
    "PUT",
    f"/_plugins/_security/api/roles/{role_name}",
    body=role
))

mapping = {
    "backend_roles": [LF2_ROLE],
    "hosts": [],
    "users": []
}

print("Mapping Lambda execution role...")
print(client.transport.perform_request(
    "PUT",
    f"/_plugins/_security/api/rolesmapping/{role_name}",
    body=mapping
))

print("LF2 OpenSearch permissions configured!")
