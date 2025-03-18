import json


def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps(
            'This is the CSV retrieval microservice from our repo!'
            )
    }
