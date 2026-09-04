import os
import io
import json
import logging
import mimetypes
from datetime import datetime
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# Boto3 import
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 is not installed yet. AWS S3 operations will require boto3.")

# Load configurations from config or environment
try:
    from config import (
        AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY,
        AWS_DEFAULT_REGION,
        AWS_S3_BUCKET_NAME,
        AWS_S3_BASE_FOLDER,
        AWS_S3_AGENT_FOLDER
    )
except ImportError:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME", "agent-initiative-bucket")
    AWS_S3_BASE_FOLDER = os.getenv("AWS_S3_BASE_FOLDER", "Agents_Doc")
    AWS_S3_AGENT_FOLDER = os.getenv("AWS_S3_AGENT_FOLDER", "Agent_22")

# Database write helper
from db import execute_write, execute_query


def get_s3_client():
    """
    Initializes and returns a boto3 S3 client using configured credentials or environment.
    """
    if not BOTO3_AVAILABLE:
        raise RuntimeError("boto3 library is not available. Please install boto3.")
    
    client_kwargs = {
        "region_name": AWS_DEFAULT_REGION or "us-east-1"
    }
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        client_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
        client_kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY

    return boto3.client("s3", **client_kwargs)


def generate_s3_key(filename, base_folder=None, agent_folder=None, subfolder="input"):
    """
    Builds standard S3 object key following the pattern:
    {base_folder}/{agent_folder}/{extracted_name}/{subfolder}/{filename}
    e.g.: Agents_Doc/Agent_22/Architecture_Plan/input/Architecture_Plan.pdf
    """
    base = base_folder or os.getenv("AWS_S3_BASE_FOLDER") or AWS_S3_BASE_FOLDER or "Agents_Doc"
    agent = agent_folder or os.getenv("AWS_S3_AGENT_FOLDER") or AWS_S3_AGENT_FOLDER or "Agent_22"
    
    clean_name = os.path.basename(filename)
    extracted_name = os.path.splitext(clean_name)[0] or "unnamed_file"
    
    if subfolder:
        return f"{base}/{agent}/{extracted_name}/{subfolder}/{clean_name}"
    return f"{base}/{agent}/{extracted_name}/{clean_name}"



def upload_to_s3(file_data, bucket_name=None, s3_key=None, content_type=None, extra_args=None):
    """
    Uploads file data directly to AWS S3 without saving anything to local server disk.
    file_data can be a Werkzeug FileStorage / stream, io.BytesIO, bytes, or string.
    
    Returns:
        (success: bool, message_or_s3_url: str)
    """
    if not BOTO3_AVAILABLE:
        return False, "boto3 library is not installed"

    bucket = bucket_name or AWS_S3_BUCKET_NAME or "agent-initiative-bucket"
    if not s3_key:
        return False, "s3_key is required for S3 upload"

    # Guess MIME type if not explicitly provided
    if not content_type:
        guessed_type, _ = mimetypes.guess_type(s3_key)
        content_type = guessed_type or "application/octet-stream"

    upload_args = {"ContentType": content_type}
    if extra_args and isinstance(extra_args, dict):
        upload_args.update(extra_args)

    try:
        s3 = get_s3_client()

        # Stream directly in memory without writing to disk
        if hasattr(file_data, "read"):
            if hasattr(file_data, "seek"):
                try:
                    file_data.seek(0)
                except Exception:
                    pass
            s3.upload_fileobj(file_data, bucket, s3_key, ExtraArgs=upload_args)
        elif isinstance(file_data, str):
            data_bytes = file_data.encode("utf-8")
            s3.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=data_bytes,
                ContentType=content_type,
                **{k: v for k, v in upload_args.items() if k != "ContentType"}
            )
        elif isinstance(file_data, (bytes, bytearray)):
            s3.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
                **{k: v for k, v in upload_args.items() if k != "ContentType"}
            )
        else:
            return False, f"Unsupported file_data type: {type(file_data)}"

        region = AWS_DEFAULT_REGION or "us-east-1"
        s3_url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
        return True, s3_url

    except (BotoCoreError, ClientError) as e:
        logger.error(f"[S3 Upload Error] Failed uploading {s3_key} to bucket {bucket}: {e}")
        return False, str(e)
    except Exception as e:
        logger.error(f"[S3 Upload Exception] Unexpected error for {s3_key}: {e}")
        return False, str(e)


def download_from_s3(bucket_name=None, s3_key=None):
    """
    Downloads an object from S3 directly into an in-memory BytesIO stream.
    Zero local disk usage.
    
    Returns:
        (success: bool, stream_or_error: io.BytesIO | str, content_type: str)
    """
    if not BOTO3_AVAILABLE:
        return False, "boto3 library is not installed", None

    bucket = bucket_name or AWS_S3_BUCKET_NAME
    if not s3_key:
        return False, "s3_key is required", None

    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=bucket, Key=s3_key)
        content_type = response.get("ContentType", "application/octet-stream")
        body_stream = io.BytesIO(response["Body"].read())
        body_stream.seek(0)
        return True, body_stream, content_type
    except Exception as e:
        logger.error(f"[S3 Download Error] Could not retrieve {s3_key} from {bucket}: {e}")
        return False, str(e), None


def get_presigned_url(bucket_name=None, s3_key=None, expiration=3600):
    """
    Generates a secure pre-signed URL for direct browser access / download from S3.
    """
    if not BOTO3_AVAILABLE:
        return None
    bucket = bucket_name or AWS_S3_BUCKET_NAME
    if not s3_key:
        return None
    try:
        s3 = get_s3_client()
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        logger.error(f"[S3 Presigned URL Error] {e}")
        return None


def save_file_and_record(
    file_obj_or_bytes,
    filename,
    uploaded_by="anonymous",
    category="general",
    request_id=None,
    project_id=None,
    track_id=None,
    track_name=None,
    user_role=None,
    subfolder="input",
    extra_metadata=None,
    base_folder=None,
    agent_folder=None,
    bucket_name=None
):
    """
    Complete pure-cloud upload flow:
    1. Generates standard S3 key using configured or provided base_folder (Agents_Doc) and agent_folder.
    2. Streams data directly to S3 (no local disk storage).
    3. Records full metadata into MySQL `uploaded_files` table:
       - who uploaded (uploaded_by)
       - when uploaded (created_at)
       - where stored (s3_bucket, s3_key, s3_url)
       - format, size, mime type, category, project_id, track_id, track_name
    
    Returns:
        dict with success status, file_id, s3_key, s3_url, and file details.
    """
    original_filename = filename or "unnamed_file"
    clean_name = secure_filename(original_filename) or "uploaded_file"
    file_ext = os.path.splitext(clean_name)[1].lower().lstrip(".")
    
    # Generate S3 key with base_folder and agent_folder
    s3_key = generate_s3_key(
        clean_name,
        base_folder=base_folder,
        agent_folder=agent_folder,
        subfolder=subfolder
    )
    bucket = bucket_name or os.getenv("AWS_S3_BUCKET_NAME") or AWS_S3_BUCKET_NAME or "agent-initiative-bucket"

    # Auto-lookup track_name and project_id if track_id is provided
    if track_id:
        try:
            t_rows = execute_query("SELECT track_name, project_id FROM project_tracks WHERE id = %s", (track_id,))
            if t_rows:
                if not track_name:
                    track_name = t_rows[0].get("track_name")
                if not project_id:
                    project_id = t_rows[0].get("project_id")
        except Exception as t_err:
            logger.warning(f"Error looking up track details for track_id {track_id}: {t_err}")

    # Compute size and mime type
    mime_type, _ = mimetypes.guess_type(clean_name)
    mime_type = mime_type or "application/octet-stream"
    file_size = 0
    
    # Determine size in memory without writing to disk
    if isinstance(file_obj_or_bytes, (bytes, bytearray)):
        file_size = len(file_obj_or_bytes)
        upload_stream = io.BytesIO(file_obj_or_bytes)
    elif isinstance(file_obj_or_bytes, str):
        encoded = file_obj_or_bytes.encode("utf-8")
        file_size = len(encoded)
        upload_stream = io.BytesIO(encoded)
    elif hasattr(file_obj_or_bytes, "read"):
        raw_bytes = file_obj_or_bytes.read()
        file_size = len(raw_bytes)
        upload_stream = io.BytesIO(raw_bytes)
    else:
        return {
            "success": False,
            "error": f"Invalid file content type: {type(file_obj_or_bytes)}"
        }

    # Upload directly to S3
    success, result_msg = upload_to_s3(
        file_data=upload_stream,
        bucket_name=bucket,
        s3_key=s3_key,
        content_type=mime_type
    )

    s3_url = result_msg if success else f"https://{bucket}.s3.{AWS_DEFAULT_REGION or 'us-east-1'}.amazonaws.com/{s3_key}"

    # Log into Database table `uploaded_files`
    insert_query = """
        INSERT INTO uploaded_files (
            filename,
            file_type,
            mime_type,
            file_size,
            s3_bucket,
            s3_key,
            s3_url,
            category,
            uploaded_by,
            project_id,
            track_id,
            track_name
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        clean_name,
        file_ext,
        mime_type,
        file_size,
        bucket,
        s3_key,
        s3_url,
        category,
        uploaded_by or "anonymous",
        project_id,
        track_id,
        track_name
    )

    db_row_id = execute_write(insert_query, params)
    
    if success:
        logger.info(f"[S3 & DB Success] Saved '{clean_name}' (ID: {db_row_id}) to S3 key '{s3_key}' by '{uploaded_by}' (Track: {track_name} / {track_id})")
        return {
            "success": True,
            "id": db_row_id,
            "filename": clean_name,
            "original_filename": original_filename,
            "file_type": file_ext,
            "mime_type": mime_type,
            "file_size": file_size,
            "s3_bucket": bucket,
            "s3_key": s3_key,
            "s3_url": s3_url,
            "category": category,
            "uploaded_by": uploaded_by,
            "project_id": project_id,
            "track_id": track_id,
            "track_name": track_name,
            "created_at": datetime.utcnow().isoformat()
        }
    else:
        logger.warning(f"[S3 Notice] S3 upload returned: {result_msg}. DB record ID {db_row_id} created with key '{s3_key}'.")
        return {
            "success": False,
            "id": db_row_id,
            "s3_key": s3_key,
            "s3_url": s3_url,
            "error": result_msg,
            "filename": clean_name,
            "track_id": track_id,
            "track_name": track_name
        }

