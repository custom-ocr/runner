# Event-Driven Cloud Function - Cloud Storage Trigger

This example demonstrates how to create a Cloud Function that is automatically triggered when files are uploaded to a Cloud Storage bucket.

## How It Works

### Architecture

```
┌─────────────────┐
│  User/App       │
│  Uploads File   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Cloud Storage Bucket   │
│  (files bucket)         │
└────────┬────────────────┘
         │
         │ Event: object.finalized
         │
         ▼
┌─────────────────────────┐
│  Cloud Function v2      │
│  (process_file)         │
└─────────────────────────┘
```

### Trigger Configuration

The function is triggered by the `google.cloud.storage.object.v1.finalized` event, which fires when:
- A new file is uploaded to the bucket
- A file is overwritten in the bucket
- A file is created through Cloud Storage API

## Configuration in Terraform

### In `terraform.tfvars`

```hcl
functions = {
  file-processor = {
    runtime     = "python311"
    entry_point = "process_file"
    description = "Processes files uploaded to the files bucket"

    source_object = "file-processor.zip"

    # Event-driven functions can have 0 warm instances to save costs
    min_instance_count    = 0
    max_instance_count    = 100
    available_memory      = "512M"
    timeout_seconds       = 300

    environment_variables = {
      LOG_LEVEL   = "INFO"
      ENVIRONMENT = "dev"
    }

    # Cloud Storage trigger configuration
    event_trigger = {
      trigger_region = "us-central1"
      event_type     = "google.cloud.storage.object.v1.finalized"
      retry_policy   = "RETRY_POLICY_RETRY"
      event_filters = [
        {
          attribute = "bucket"
          value     = "your-project-dev-files"  # Your files bucket name
        }
      ]
    }

    # Event-driven functions don't need public invokers
    invoker_members = []
  }
}
```

### Key Parameters Explained

#### Event Trigger

- **`event_type`**: The type of Cloud Storage event
  - `google.cloud.storage.object.v1.finalized` - Object created/uploaded
  - `google.cloud.storage.object.v1.deleted` - Object deleted
  - `google.cloud.storage.object.v1.archived` - Object archived
  - `google.cloud.storage.object.v1.metadataUpdated` - Metadata updated

- **`event_filters`**: Filters to limit which events trigger the function
  - `bucket` - The bucket name (required)
  - `name` - Filter by object name/prefix (optional)

- **`retry_policy`**: How to handle failures
  - `RETRY_POLICY_RETRY` - Retry failed executions
  - `RETRY_POLICY_DO_NOT_RETRY` - Don't retry failures

#### Instance Configuration

For event-driven functions:
- **`min_instance_count = 0`**: Save costs by not keeping warm instances
- **`max_instance_count`**: Limit maximum concurrent executions
- Functions will auto-scale from 0 to max based on events

## Function Code Structure

### CloudEvent Object

The function receives a `CloudEvent` object with the following data:

```python
{
    "bucket": "your-project-dev-files",
    "name": "path/to/file.jpg",
    "contentType": "image/jpeg",
    "size": 1234567,
    "timeCreated": "2024-01-15T10:30:00.000Z",
    "updated": "2024-01-15T10:30:00.000Z",
    "generation": "1234567890",
    "metageneration": "1"
}
```

### Example Function

```python
import functions_framework
from cloudevents.http import CloudEvent

@functions_framework.cloud_event
def process_file(cloud_event: CloudEvent) -> None:
    data = cloud_event.data

    bucket_name = data["bucket"]
    file_name = data["name"]
    content_type = data.get("contentType")
    size = data.get("size")

    print(f"Processing: {file_name} from {bucket_name}")

    # Add your processing logic here
```

## Deployment

### 1. Build the Function

```bash
cd examples/event-driven-function
zip -r file-processor.zip main.py requirements.txt
```

### 2. Update `terraform.tfvars`

Make sure the bucket name in `event_filters` matches your files bucket:

```hcl
event_filters = [
  {
    attribute = "bucket"
    value     = "YOUR_PROJECT_ID-dev-files"  # Replace with actual bucket name
  }
]
```

### 3. Deploy Infrastructure

```bash
cd ../../
./scripts/deploy-infra.sh dev
```

### 4. Upload Function Code

```bash
./scripts/upload-function.sh dev examples/event-driven-function/file-processor.zip
```

### 5. Deploy Function

```bash
./scripts/deploy-functions.sh dev
```

## Testing

### Upload a Test File

```bash
# Upload a file to trigger the function
echo "Hello World" > test.txt
gsutil cp test.txt gs://YOUR_PROJECT_ID-dev-files/
```

### View Logs

```bash
# View function logs
gcloud functions logs read file-processor --region=us-central1 --gen2

# Or use Cloud Console
# https://console.cloud.google.com/functions
```

## Advanced Patterns

### Filter by File Extension

```hcl
event_filters = [
  {
    attribute = "bucket"
    value     = "your-project-dev-files"
  },
  {
    attribute = "name"
    value     = "*.jpg"  # Only trigger for .jpg files
  }
]
```

### Filter by Path Prefix

```hcl
event_filters = [
  {
    attribute = "bucket"
    value     = "your-project-dev-files"
  },
  {
    attribute = "name"
    value     = "uploads/*"  # Only files in uploads/ folder
  }
]
```

### Multiple Functions for Different File Types

```hcl
functions = {
  image-processor = {
    # ... config ...
    event_filters = [
      {
        attribute = "bucket"
        value     = "your-project-dev-files"
      },
      {
        attribute = "name"
        value     = "images/*"
      }
    ]
  }

  document-processor = {
    # ... config ...
    event_filters = [
      {
        attribute = "bucket"
        value     = "your-project-dev-files"
      },
      {
        attribute = "name"
        value     = "documents/*"
      }
    ]
  }
}
```

## Common Use Cases

### 1. Image Processing (OCR)

```python
from google.cloud import vision

@functions_framework.cloud_event
def process_image(cloud_event: CloudEvent) -> None:
    data = cloud_event.data
    bucket = data["bucket"]
    filename = data["name"]

    # Perform OCR
    client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = f"gs://{bucket}/{filename}"

    response = client.text_detection(image=image)
    text = response.text_annotations[0].description if response.text_annotations else ""

    print(f"Extracted text: {text}")
```

### 2. File Validation

```python
@functions_framework.cloud_event
def validate_file(cloud_event: CloudEvent) -> None:
    data = cloud_event.data
    content_type = data.get("contentType", "")
    size = data.get("size", 0)

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if content_type not in allowed_types:
        print(f"Invalid file type: {content_type}")
        # Delete invalid file or move to quarantine bucket
        return

    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024
    if size > max_size:
        print(f"File too large: {size} bytes")
        return

    print("File validation passed")
```

### 3. Metadata Extraction

```python
from google.cloud import storage
import json

@functions_framework.cloud_event
def extract_metadata(cloud_event: CloudEvent) -> None:
    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]

    # Create metadata
    metadata = {
        "filename": file_name,
        "size": data.get("size"),
        "content_type": data.get("contentType"),
        "uploaded_at": data.get("timeCreated"),
        "bucket": bucket_name
    }

    # Save metadata (e.g., to Firestore, BigQuery, etc.)
    print(f"Metadata: {json.dumps(metadata)}")
```

## Monitoring

### Key Metrics to Monitor

- **Invocations**: Number of times function is triggered
- **Execution Time**: How long each invocation takes
- **Errors**: Failed executions
- **Memory Usage**: Peak memory consumption
- **Active Instances**: Number of running instances

### Set Up Alerts

```bash
# Create alert for function errors
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="Function Errors" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s
```

## Cost Optimization

### For Event-Driven Functions

- Set `min_instance_count = 0` to avoid paying for idle instances
- Use appropriate memory allocation (don't over-provision)
- Set reasonable timeouts to avoid long-running executions
- Consider using retry policies to handle transient failures

### Estimated Costs

For 1 million invocations per month:
- With 0 warm instances: ~$0.40 (invocations + compute)
- With 2 warm instances: ~$14.00 (invocations + compute + idle time)

## Troubleshooting

### Function Not Triggering

1. **Check bucket name** in event_filters matches exactly
2. **Verify IAM permissions** - Function needs `storage.objects.get`
3. **Check function logs** for deployment errors
4. **Verify event type** is correct

### Permission Errors

```bash
# Grant Storage permissions to function's service account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
  --role="roles/storage.objectViewer"
```

### Debugging

```python
# Add detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

@functions_framework.cloud_event
def process_file(cloud_event: CloudEvent) -> None:
    logging.debug(f"Cloud Event: {cloud_event}")
    logging.debug(f"Event Data: {cloud_event.data}")
    # ... rest of function
```

## References

- [Cloud Functions Event Types](https://cloud.google.com/functions/docs/calling/storage)
- [CloudEvents Specification](https://cloudevents.io/)
- [Cloud Storage Events](https://cloud.google.com/storage/docs/pubsub-notifications)
