import os
import time
from datetime import datetime, timezone
from decimal import Decimal

import boto3
import requests
from requests.exceptions import RequestException

API_KEY = os.environ["YELP_API_KEY"]
TABLE_NAME = "yelp-restaurants"
REGION = "us-east-1"

CUISINES = {
    "Italian": "italian",
    "Chinese": "chinese",
    "Indian": "indpak",
    "Japanese": "japanese",
    "Mexican": "mexican",
}

NEIGHBORHOODS = [
    "Chelsea",
    "SoHo",
    "Midtown",
    "Upper East Side",
    "Upper West Side",
    "East Village",
    "West Village",
    "Greenwich Village",
    "Lower East Side",
    "Chinatown",
    "Financial District",
    "Tribeca",
    "Hell's Kitchen",
    "Harlem",
    "Murray Hill",
    "Gramercy",
    "Flatiron District",
    "Washington Heights",
]

TARGET_PER_CUISINE = 200
PAGE_SIZE = 40
MAX_RESULTS_PER_SEARCH = 240

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)


def fetch_restaurants(category, offset, neighborhood):
    response = requests.get(
        "https://api.yelp.com/v3/businesses/search",
        headers={
            "Authorization": f"Bearer {API_KEY}"
        },
        params={
            "location": f"{neighborhood}, Manhattan, New York, NY",
            "categories": category,
            "limit": PAGE_SIZE,
            "offset": offset,
        },
        timeout=30,
    )

    if response.status_code != 200:
        print(
            f"Yelp error {response.status_code}: "
            f"{response.text[:400]}"
        )

    response.raise_for_status()
    return response.json().get("businesses", [])


def load_existing_restaurants():
    existing = {}

    response = table.scan(
        ProjectionExpression="BusinessID, Cuisine"
    )

    while True:
        for item in response.get("Items", []):
            business_id = item["BusinessID"]
            cuisine = item.get("Cuisine")

            existing[business_id] = cuisine

        if "LastEvaluatedKey" not in response:
            break

        response = table.scan(
            ProjectionExpression="BusinessID, Cuisine",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )

    return existing


def main():
    print("Checking existing DynamoDB restaurants...")

    existing = load_existing_restaurants()
    seen = set(existing)

    cuisine_counts = {
        cuisine: sum(
            1 for saved_cuisine in existing.values()
            if saved_cuisine == cuisine
        )
        for cuisine in CUISINES
    }

    total_new = 0

    print(f"Existing restaurants: {len(seen)}")

    with table.batch_writer() as batch:

        for cuisine, category in CUISINES.items():

            cuisine_count = cuisine_counts[cuisine]

            print(f"\nFetching {cuisine} restaurants...")
            print(f"Already stored: {cuisine_count}")

            if cuisine_count >= TARGET_PER_CUISINE:
                print(f"{cuisine} target already reached.")
                continue

            for neighborhood in NEIGHBORHOODS:

                if cuisine_count >= TARGET_PER_CUISINE:
                    break

                print(f"\nSearching {neighborhood}...")

                for offset in range(
                    0,
                    MAX_RESULTS_PER_SEARCH,
                    PAGE_SIZE
                ):

                    if cuisine_count >= TARGET_PER_CUISINE:
                        break

                    try:
                        restaurants = fetch_restaurants(
                            category,
                            offset,
                            neighborhood
                        )
                    except RequestException as error:
                        print(f"Request failed: {error}")
                        print("Stopping to avoid repeated API errors.")
                        return

                    if not restaurants:
                        break

                    for business in restaurants:

                        if cuisine_count >= TARGET_PER_CUISINE:
                            break

                        business_id = business.get("id")

                        if not business_id or business_id in seen:
                            continue

                        location = business.get("location") or {}

                        # Initial city-label filter.
                        if location.get("city", "").strip().lower() not in (
                            "new york",
                            "manhattan",
                        ):
                            continue

                        coordinates = business.get("coordinates") or {}

                        latitude = coordinates.get("latitude")
                        longitude = coordinates.get("longitude")

                        if latitude is None or longitude is None:
                            continue

                        item = {
                            "BusinessID": business_id,
                            "Name": business.get("name", ""),
                            "Cuisine": cuisine,
                            "Address": ", ".join(
                                location.get("display_address") or []
                            ),
                            "ZipCode": location.get("zip_code", ""),
                            "Latitude": Decimal(str(latitude)),
                            "Longitude": Decimal(str(longitude)),
                            "Rating": Decimal(
                                str(business.get("rating") or 0)
                            ),
                            "ReviewCount": business.get(
                                "review_count"
                            ) or 0,
                            "InsertedAtTimestamp": datetime.now(
                                timezone.utc
                            ).isoformat(),
                        }

                        batch.put_item(Item=item)

                        seen.add(business_id)
                        cuisine_count += 1
                        total_new += 1

                    print(
                        f"{cuisine}: {cuisine_count}/{TARGET_PER_CUISINE} "
                        f"| Total unique: {len(seen)}"
                    )

                    if len(restaurants) < PAGE_SIZE:
                        break

                    time.sleep(0.5)

            cuisine_counts[cuisine] = cuisine_count

            print(
                f"\nCompleted {cuisine}: "
                f"{cuisine_count} restaurants"
            )

    print("\n================================")
    print("IMPORT SUMMARY")
    print("================================")

    for cuisine, count in cuisine_counts.items():
        print(f"{cuisine}: {count}")

    print(f"\nNew restaurants imported: {total_new}")
    print(f"Total unique restaurants: {len(seen)}")
    print("================================")


if __name__ == "__main__":
    main()