import json
import os
import random
import boto3
from botocore.config import Config

# Retrieve API key from environment variable
BEDROCK_API_KEY = os.environ.get('BEDROCK_API_KEY')

# Pass Bearer Token header to boto3 botocore event hooks (if required by custom gateway endpoint)
config = Config(region_name='us-east-1')
bedrock = boto3.client('bedrock-runtime', config=config)

if BEDROCK_API_KEY:
    def add_auth_header(request, **kwargs):
        request.headers['Authorization'] = f"Bearer {BEDROCK_API_KEY}"
    bedrock.meta.events.register('before-send.bedrock-runtime.*', add_auth_header)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CloudFacts')

def lambda_handler(event, context):
    try:
        # 1. Fetch random item from DynamoDB
        random_id = str(random.randint(1, 3))
        db_response = table.get_item(Key={'FactID': random_id})
        raw_fact = db_response.get('Item', {}).get(
            'fact', 
            'AWS S3 was launched in 2006 as one of the first cloud services.'
        )

        # 2. Format prompt
        prompt = f"Make this cloud computing fact witty, short, and engaging for a developer: '{raw_fact}'"
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 150,
            "messages": [{"role": "user", "content": prompt}]
        })

        # 3. Invoke Bedrock using an active inference profile
        bedrock_response = bedrock.invoke_model(
            modelId="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            contentType="application/json",
            accept="application/json",
            body=body
        )
        
        response_body = json.loads(bedrock_response['body'].read())
        witty_fact = response_body['content'][0]['text']

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "OPTIONS,GET"
            },
            "body": json.dumps({"fact": witty_fact})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)})
        }