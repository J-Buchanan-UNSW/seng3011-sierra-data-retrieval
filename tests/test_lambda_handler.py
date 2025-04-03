import json
from unittest.mock import MagicMock
from lambda_functions.retrievalCSV.lambda_function import lambda_handler


def test_lambda_handler_no_params():
    # The CSV content that will be "returned" from S3
    csv_content = 'col1,col2,col3\nval1,val2,val3\nval4,val5,val6'

    # Create a mock S3 client
    mock_s3_client = MagicMock()

    # Configure the mock to return our CSV content
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    # Prepare the event and context
    event = {
        "queryStringParameters": {}
    }
    context = {}

    # Call the lambda handler function with our mock S3 client
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    # Assert that get_object was called with correct parameters
    mock_s3_client.get_object.assert_called_once_with(
        Bucket='dev-sierra-e-bucket',
        Key='processedCSV/environmental_risk.csv'
    )

    # Assert the response structure
    assert response['statusCode'] == 200
    assert 'Content-Type' in response['headers']
    assert response['headers']['Content-Type'] == 'application/json'

    # Parse the response body
    response_body = json.loads(response['body'])

    # Verify the response data
    assert len(response_body) == 2  # Two rows of data
    assert 'col1' in response_body[0]
    assert 'col2' in response_body[0]
    assert 'col3' in response_body[0]
    assert response_body[0]['col1'] == 'val1'
    assert response_body[1]['col1'] == 'val4'


def test_lambda_handler_with_filter():
    # The CSV content that will be "returned" from S3
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'

    # Create a mock S3 client
    mock_s3_client = MagicMock()

    # Configure the mock to return our CSV content
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    # Prepare the event with filter parameters
    event = {
        "queryStringParameters": {
            "filter": "value > 100"
        }
    }
    context = {}

    # Call the lambda handler function with our mock S3 client
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    # Assert that get_object was called with correct parameters
    mock_s3_client.get_object.assert_called_once_with(
        Bucket='dev-sierra-e-bucket',
        Key='processedCSV/environmental_risk.csv'
    )

    # Parse the response body
    response_body = json.loads(response['body'])

    # Verify filtered and sorted data

    # Should only include beta and gamma
    assert len(response_body) == 2

    # First item should be beta
    assert response_body[0]['value'] == 200

    # Second item should be gamma
    assert response_body[1]['value'] == 300


def test_lambda_handler_with_columns():
    # The CSV content that will be "returned" from S3
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'

    # Create a mock S3 client
    mock_s3_client = MagicMock()

    # Configure the mock to return our CSV content
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    # Prepare the event with filter parameters
    event = {
        "queryStringParameters": {
            "columns": "id,value"
        }
    }
    context = {}

    # Call the lambda handler function with our mock S3 client
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    # Assert that get_object was called with correct parameters
    mock_s3_client.get_object.assert_called_once_with(
        Bucket='dev-sierra-e-bucket',
        Key='processedCSV/environmental_risk.csv'
    )

    # Parse the response body
    response_body = json.loads(response['body'])

    # Verify filtered and sorted data

    # Should include all
    assert len(response_body) == 3

    # Assert name is not in response body
    assert 'name' not in response_body[0]

    # First item should be alpha
    assert response_body[0]['value'] == 100

    # Second item should be beta
    assert response_body[1]['value'] == 200

    # Third item should be gamma
    assert response_body[2]['value'] == 300


def test_lambda_handler_with_order():
    # The CSV content that will be "returned" from S3
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'

    # Create a mock S3 client
    mock_s3_client = MagicMock()

    # Configure the mock to return our CSV content
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    # Prepare the event with filter parameters
    event = {
        "queryStringParameters": {
            "order_by": "value desc"
        }
    }
    context = {}

    # Call the lambda handler function with our mock S3 client
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    # Assert that get_object was called with correct parameters
    mock_s3_client.get_object.assert_called_once_with(
        Bucket='dev-sierra-e-bucket',
        Key='processedCSV/environmental_risk.csv'
    )

    # Parse the response body
    response_body = json.loads(response['body'])

    # Verify filtered and sorted data

    # Should include all
    assert len(response_body) == 3

    # First item should be gamma
    assert response_body[0]['value'] == 300

    # Second item should be beta
    assert response_body[1]['value'] == 200

    # Third item should be alpha
    assert response_body[2]['value'] == 100


def test_lambda_handler_all_params():
    # The CSV content that will be "returned" from S3
    csv_content = 'id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300'

    # Create a mock S3 client
    mock_s3_client = MagicMock()

    # Configure the mock to return our CSV content
    mock_body = MagicMock()
    mock_body.read.return_value = csv_content.encode('utf-8')
    mock_s3_client.get_object.return_value = {'Body': mock_body}

    # Prepare the event with filter parameters
    event = {
        "queryStringParameters": {
            "filter": "value > 100",
            "columns": "id,value",
            "order_by": "value desc"
        }
    }
    context = {}

    # Call the lambda handler function with our mock S3 client
    response = lambda_handler(event, context, s3_client=mock_s3_client)

    # Assert that get_object was called with correct parameters
    mock_s3_client.get_object.assert_called_once_with(
        Bucket='dev-sierra-e-bucket',
        Key='processedCSV/environmental_risk.csv'
    )

    # Parse the response body
    response_body = json.loads(response['body'])

    # Verify filtered and sorted data

    # Assert name is not in response body
    assert 'name' not in response_body[0]

    # Should include beta and gamma
    assert len(response_body) == 2

    # First item should be gamma
    assert response_body[0]['value'] == 300

    # Second item should be beta
    assert response_body[1]['value'] == 200
