import os
import io
import json
import logging
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from utils.s3_utils import (
    upload_to_s3,
    download_from_s3,
    get_presigned_url,
    save_file_and_record,
    generate_s3_key
)
from db import execute_query, execute_write
from config import (
    AWS_S3_BUCKET_NAME,
    AWS_S3_BASE_FOLDER,
    AWS_S3_AGENT_FOLDER
)

logger = logging.getLogger(__name__)

upload_bp = Blueprint("upload", __name__)


def success_response(data=None, status_code=200):
    response = {"success": True}
    if data:
        response.update(data)
    return jsonify(response), status_code


def error_response(message, status_code=400):
    return jsonify({"success": False, "message": message}), status_code


@upload_bp.route("/s3/upload", methods=["POST"])
@upload_bp.route("/s3", methods=["POST"])
@upload_bp.route("/uploads/s3", methods=["POST"])
@upload_bp.route("/uploads", methods=["POST"])
def upload_s3_only():

    """
    Reference Implementation & Pure Cloud S3 Upload:
    Uploads any files (pdf, docx, excel, image, ppt, text, mermaid diagrams, etc.) directly to S3.
    Nothing is saved on the local server disk.
    Records metadata (who uploaded, when uploaded, exact S3 location, format, size, category) in MySQL table `uploaded_files`.
    """
    try:
        # Retrieve files from request
        files = request.files.getlist("files") or request.files.getlist("file") or request.files.getlist("file_upload")
        if not files or all(not f.filename for f in files):
            return error_response("No files provided for upload", status_code=400)

        bucket_name = request.form.get("bucket_name") or os.getenv("AWS_S3_BUCKET_NAME") or AWS_S3_BUCKET_NAME or "agent-initiative-bucket"
        base_folder = request.form.get("base_folder") or os.getenv("AWS_S3_BASE_FOLDER") or AWS_S3_BASE_FOLDER or "Agents_Doc"
        agent_folder = request.form.get("agent_folder") or os.getenv("AWS_S3_AGENT_FOLDER") or AWS_S3_AGENT_FOLDER or "Agent_22"
        
        # User & context metadata
        uploaded_by = request.form.get("uploaded_by") or request.headers.get("X-User-Id") or "anonymous"
        user_role = request.form.get("user_role") or request.headers.get("X-User-Role")
        category = request.form.get("category", "general_upload")
        raw_request_id = request.form.get("request_id")
        request_id = int(raw_request_id) if raw_request_id and str(raw_request_id).isdigit() else None
        raw_project_id = request.form.get("project_id")
        project_id = int(raw_project_id) if raw_project_id and str(raw_project_id).isdigit() else None

        uploaded_records = []
        uploaded_keys = []
        failed_files = []

        for file in files:
            if not file or not file.filename:
                continue

            extracted_name = os.path.splitext(file.filename)[0]
            clean_filename = secure_filename(file.filename) or file.filename
            s3_base_path = f"{base_folder}/{agent_folder}/{extracted_name}"
            input_key = f"{s3_base_path}/input/{clean_filename}"

            # Stream directly to S3 and log to MySQL table `uploaded_files`
            record = save_file_and_record(
                file_obj_or_bytes=file.stream,
                filename=file.filename,
                uploaded_by=uploaded_by,
                category=category,
                request_id=request_id,
                project_id=project_id,
                user_role=user_role,
                subfolder="input",
                base_folder=base_folder,
                agent_folder=agent_folder,
                bucket_name=bucket_name
            )


            if record.get("success"):
                uploaded_keys.append(record.get("s3_key", input_key))
                uploaded_records.append(record)
                print(f"[AWS S3 Fast] Successfully saved '{file.filename}' to S3 key '{input_key}' for user '{uploaded_by}'.", flush=True)
            else:
                err = record.get("error", "Unknown error")
                failed_files.append({"filename": file.filename, "error": err, "record": record})
                # If record ID was created in DB, still include in keys for traceability
                uploaded_keys.append(record.get("s3_key", input_key))
                uploaded_records.append(record)
                print(f"[AWS S3 Fast] S3 note for '{file.filename}': {err}", flush=True)

        return success_response({
            "message": "Uploaded to S3",
            "keys": uploaded_keys,
            "records": uploaded_records,
            "failed": failed_files
        })

    except Exception as e:
        logger.error(f"Error in upload_s3_only: {e}", exc_info=True)
        return error_response(f"S3 upload failed: {str(e)}", status_code=500)


@upload_bp.route("/uploads/diagram", methods=["POST"])
@upload_bp.route("/diagram", methods=["POST"])
def upload_diagram():
    """
    Uploads diagrams (e.g. Mermaid .mmd, SVG, PNG, JSON architecture specs) directly to S3
    and records in database without saving locally.
    """
    try:
        data = request.json or {}
        diagram_text = data.get("diagram") or data.get("mermaid_diagram")
        filename = data.get("filename", "architecture_diagram.mmd")
        uploaded_by = data.get("uploaded_by") or request.headers.get("X-User-Id") or "anonymous"
        category = "mermaid_diagram"
        request_id = data.get("request_id")
        project_id = data.get("project_id")

        if not diagram_text:
            return error_response("Diagram content is required", status_code=400)

        record = save_file_and_record(
            file_obj_or_bytes=diagram_text,
            filename=filename,
            uploaded_by=uploaded_by,
            category=category,
            request_id=request_id,
            project_id=project_id,
            subfolder="diagrams",
            base_folder=data.get("base_folder") or os.getenv("AWS_S3_BASE_FOLDER") or "Agents_Doc",
            agent_folder=data.get("agent_folder") or os.getenv("AWS_S3_AGENT_FOLDER") or "Agent_22"
        )


        return success_response({
            "message": "Diagram processed for S3",
            "record": record
        })

    except Exception as e:
        logger.error(f"Error in upload_diagram: {e}", exc_info=True)
        return error_response(f"Diagram upload failed: {str(e)}", status_code=500)


@upload_bp.route("/uploads", methods=["GET"])
@upload_bp.route("/uploads/list", methods=["GET"])
def list_uploaded_files():
    """
    Retrieves file upload records from database with optional filters:
    - category
    - uploaded_by
    - request_id
    - project_id
    """
    try:
        category = request.args.get("category")
        uploaded_by = request.args.get("uploaded_by")
        request_id = request.args.get("request_id")
        project_id = request.args.get("project_id")
        limit = min(int(request.args.get("limit", 50)), 200)
        offset = int(request.args.get("offset", 0))

        conditions = []
        params = []

        if category:
            conditions.append("category = %s")
            params.append(category)
        if uploaded_by:
            conditions.append("uploaded_by = %s")
            params.append(uploaded_by)
        if request_id:
            conditions.append("request_id = %s")
            params.append(request_id)
        if project_id:
            conditions.append("project_id = %s")
            params.append(project_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT id, filename, original_filename, file_type, mime_type, file_size,
                   s3_bucket, s3_key, s3_url, category, uploaded_by, user_role,
                   request_id, project_id, metadata_json, created_at
            FROM uploaded_files
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        results = execute_query(query, tuple(params))

        for row in results:
            if row.get("created_at"):
                row["created_at"] = str(row["created_at"])

        return success_response({"files": results, "count": len(results)})

    except Exception as e:
        logger.error(f"Error listing uploaded files: {e}", exc_info=True)
        return error_response(f"Failed to list files: {str(e)}", status_code=500)


@upload_bp.route("/uploads/<int:file_id>", methods=["GET"])
def get_file_metadata(file_id):
    """
    Retrieves a single file's metadata and generates a presigned S3 download URL.
    """
    try:
        rows = execute_query("SELECT * FROM uploaded_files WHERE id = %s", (file_id,))
        if not rows:
            return error_response("File not found", status_code=404)

        file_meta = rows[0]
        if file_meta.get("created_at"):
            file_meta["created_at"] = str(file_meta["created_at"])

        # Generate pre-signed URL for direct browser access
        presigned_url = get_presigned_url(
            bucket_name=file_meta.get("s3_bucket"),
            s3_key=file_meta.get("s3_key")
        )
        file_meta["presigned_url"] = presigned_url

        return success_response({"file": file_meta})

    except Exception as e:
        logger.error(f"Error fetching file metadata: {e}", exc_info=True)
        return error_response(f"Error: {str(e)}", status_code=500)


@upload_bp.route("/uploads/<int:file_id>/download", methods=["GET"])
def download_file_stream(file_id):

    """
    Streams file bytes directly from S3 to client without saving to local server disk.
    """
    try:
        rows = execute_query("SELECT * FROM uploaded_files WHERE id = %s", (file_id,))
        if not rows:
            return error_response("File record not found", status_code=404)

        record = rows[0]
        bucket = record.get("s3_bucket")
        key = record.get("s3_key")
        filename = record.get("original_filename") or record.get("filename")
        mime = record.get("mime_type") or "application/octet-stream"

        success, stream_or_err, s3_mime = download_from_s3(bucket, key)
        if not success:
            return error_response(f"Could not retrieve file from S3: {stream_or_err}", status_code=502)

        return send_file(
            stream_or_err,
            mimetype=s3_mime or mime,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error streaming file from S3: {e}", exc_info=True)
        return error_response(f"Download failed: {str(e)}", status_code=500)
