import json
import uuid
import boto3

lex = boto3.client("lexv2-runtime", region_name="us-east-1")

BOT_ID = "DGFWHSB6NI"
BOT_ALIAS_ID = "TSTALIASID"
LOCALE_ID = "en_US"


def lambda_handler(event, context):
    try:
        body = event.get("body") or {}
        if isinstance(body, str):
            body = json.loads(body)

        messages = body.get("messages") or []
        if not messages:
            raise ValueError("No messages provided")

        user_text = messages[-1]["unstructured"]["text"]

        # Reuse the session ID supplied by the frontend when possible.
        session_id = (
            body.get("sessionId")
            or event.get("requestContext", {}).get("requestId")
            or str(uuid.uuid4())
        )

        response = lex.recognize_text(
            botId=BOT_ID,
            botAliasId=BOT_ALIAS_ID,
            localeId=LOCALE_ID,
            sessionId=str(session_id),
            text=user_text
        )

        replies = [
            {
                "type": "unstructured",
                "unstructured": {"text": message["content"]}
            }
            for message in response.get("messages", [])
            if message.get("contentType") == "PlainText"
        ]

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "messages": replies,
                "sessionId": str(session_id)
            })
        }

    except Exception as error:
        print("LF0 error:", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "messages": [
                    {
                        "type": "unstructured",
                        "unstructured": {
                            "text": "Sorry, something went wrong."
                        }
                    }
                ]
            })
        }
