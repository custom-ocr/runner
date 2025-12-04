"""
Cloud Function triggered by Cloud Storage events
This function is triggered when a file is uploaded to the files bucket
"""

import functions_framework
from cloudevents.http import CloudEvent


@functions_framework.cloud_event
def process_file(cloud_event: CloudEvent) -> None:
    """
    Triggered when a file is uploaded to Cloud Storage

    Args:
        cloud_event: CloudEvent object containing event data
    """

    # Get event data
    data = cloud_event.data

    # Extract file information
    bucket_name = data["bucket"]
    file_name = data["name"]
    content_type = data.get("contentType", "unknown")
    size = data.get("size", 0)
    time_created = data.get("timeCreated")

    print(f"Processing file upload:")
    print(f"  Bucket: {bucket_name}")
    print(f"  File: {file_name}")
    print(f"  Content Type: {content_type}")
    print(f"  Size: {size} bytes")
    print(f"  Created: {time_created}")

    # Add your custom processing logic here
    # Examples:
    # - Process images with OCR
    # - Extract text from PDFs
    # - Validate file format
    # - Trigger other workflows
    # - Store metadata in database

    try:
        # Example: Log to Cloud Logging
        print(f"Successfully processed file: {file_name}")

        # Example: You can download the file for processing
        # from google.cloud import storage
        # storage_client = storage.Client()
        # bucket = storage_client.bucket(bucket_name)
        # blob = bucket.blob(file_name)
        # file_contents = blob.download_as_bytes()

        # Example: Process the file
        # result = your_processing_function(file_contents)

    except Exception as e:
        print(f"Error processing file {file_name}: {str(e)}")
        raise


