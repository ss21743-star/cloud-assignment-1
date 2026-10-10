# Dining Concierge Chatbot

**Cloud Computing and Big Data — Fall 2026**  
**Homework Assignment 1 | New York University**

**GitHub Repository:** https://github.com/ss21743-star/cloud-assignment-1

## Project Overview

Dining Concierge is a serverless, event-driven chatbot built using Amazon Web Services (AWS). The application allows users to request restaurant recommendations through a conversational web interface.

Users provide their preferred location, cuisine, number of people, dining date and time, and email address. The application processes the request asynchronously and emails three restaurant recommendations.

## System Architecture

```text
User / Web Browser
        |
        v
Amazon S3 (Frontend)
        |
        v
Amazon API Gateway
        |
        v
AWS Lambda (LF0)
        |
        v
Amazon Lex (Chatbot)
        |
        v
AWS Lambda (LF1)
        |
        v
Amazon SQS (Q1)
        |
        v
EventBridge Scheduler → Lambda (LF2)
                            |
                    +-------+-------+
                    |               |
                    v               v
                OpenSearch       DynamoDB
                    |               |
                    +-------+-------+
                            |
                            v
                        Amazon SES
                            |
                            v
                  Recommendation Email
```

An additional DynamoDB table stores previous searches to support the extra-credit feature.

## AWS Services Used

| AWS Service | Purpose |
|---|---|
| Amazon S3 | Hosts the static chatbot frontend |
| API Gateway | Connects the frontend to the backend |
| AWS Lambda LF0 | Communicates with Amazon Lex |
| Amazon Lex | Manages conversations and collects dining preferences |
| AWS Lambda LF1 | Validates inputs and sends requests to SQS |
| Amazon SQS | Stores dining requests for asynchronous processing |
| EventBridge Scheduler | Invokes LF2 every minute |
| AWS Lambda LF2 | Processes requests and prepares recommendations |
| Amazon OpenSearch | Searches restaurants by cuisine |
| Amazon DynamoDB | Stores restaurant data and previous search history |
| Amazon SES | Sends restaurant recommendation emails |

## Amazon Lex Chatbot

The `DiningConciergeBot` contains four intents:

- **GreetingIntent:** Handles greetings.
- **ThankYouIntent:** Responds to thank-you messages.
- **DiningSuggestionsIntent:** Collects information required to recommend restaurants.
- **FallbackIntent:** Handles unrecognized messages.

The DiningSuggestionsIntent collects six slots:

1. Location
2. Cuisine
3. NumberOfPeople
4. DiningTime (date)
5. DiningHour (time)
6. Email

## Restaurant Dataset

The application stores **1,000 restaurant records** in the DynamoDB table `yelp-restaurants`.

The dataset includes five cuisines:

- Chinese
- Indian
- Italian
- Japanese
- Mexican

Each cuisine contains 200 restaurant records.

Restaurant attributes include BusinessID, Name, Cuisine, Address, Rating, ReviewCount, Latitude, Longitude, ZipCode, and insertedAtTimestamp.

Restaurant identifiers and cuisine information are indexed in Amazon OpenSearch for efficient retrieval.

## Application Workflow

1. The user opens the chatbot frontend hosted on Amazon S3.
2. API Gateway forwards chatbot requests to Lambda LF0.
3. LF0 communicates with Amazon Lex using `recognize_text`.
4. Lex collects the required dining preferences.
5. Lambda LF1 validates the information and sends the request to SQS Q1.
6. EventBridge Scheduler invokes Lambda LF2 every minute.
7. LF2 retrieves matching restaurant IDs from OpenSearch.
8. Full restaurant details are fetched from DynamoDB.
9. Amazon SES sends three restaurant recommendations to the user's email.
10. Successfully processed messages are deleted from SQS.

## Extra Credit: Previous Search Recognition

The application includes a feature to recognize repeated restaurant searches.

The DynamoDB table `dining-search-state` stores previous search details, including location, cuisine, and selected restaurant IDs.

When a user repeats the same location and cuisine within the same chat session, the chatbot asks whether they want the previous recommendations.

- **Yes:** Reuses the previously selected restaurants.
- **No:** Generates a new selection of recommendations.

## Repository Structure

```text
cloud-assignment-1/
├── frontend/
│   └── Static website and chatbot assets
├── lambda-functions/
│   └── AWS Lambda source code
├── other-scripts/
│   └── Restaurant ingestion and indexing scripts
└── README.md
```

## Deployment

**Frontend:**

http://ss21743-cloud-assignment1-frontend.s3-website-us-east-1.amazonaws.com/chat.html

**API Gateway endpoint:**

https://wj83v6r5ge.execute-api.us-east-1.amazonaws.com/prod/chatbot

**AWS Region:** `us-east-1` (N. Virginia)

**EventBridge Schedule:** `rate(1 minutes)`

The application requires the deployed AWS resources to remain active. The frontend URL may become unavailable once these resources are decommissioned.

## Testing

The application supports the following end-to-end demonstration:

1. Open the chatbot frontend.
2. Enter a greeting.
3. Request restaurant suggestions.
4. Provide dining preferences.
5. Receive confirmation from the chatbot.
6. Check the email inbox for restaurant recommendations.
7. Repeat a previous search to demonstrate the extra-credit Yes/No workflow.

**Note:** Amazon SES sandbox restrictions apply until production access is approved. In sandbox mode, recipient addresses must be verified.

## GitHub Release

**Final Submission — v1.0**

https://github.com/ss21743-star/cloud-assignment-1/releases/tag/v1.0

The GitHub Release contains the assignment ZIP file and project source code.

## Resource Cleanup

All AWS resources should be reviewed after assignment evaluation. Billable resources should be decommissioned to avoid unnecessary charges, and no orphaned resources should be left running.
