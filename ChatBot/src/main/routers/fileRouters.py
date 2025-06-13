from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Form, Depends
from fastapi.responses import FileResponse
import os


from src.main.dependencies import get_agent_files_upload_dir, get_log_dir_path
from src.app.utils.loggerConfig import LoggerManager as lg

router = APIRouter()

def get_unique_filename(directory, filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(directory, unique_filename)):
        unique_filename = f"{base}({counter}){ext}"
        counter += 1
    return unique_filename

async def async_save_uploaded_file(file: UploadFile, username: str, logger, agent_files_upload_dir):
    safe_username = "".join(c for c in username if c.isalnum() or c in ('-', '_')).lower()
    folder_name = os.path.join(agent_files_upload_dir, safe_username)
    os.makedirs(folder_name, exist_ok=True)
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ('-', '_', '.', '(', ')'))
    unique_filename = get_unique_filename(folder_name, safe_filename)
    file_location = os.path.join(folder_name, unique_filename)

    size = 0
    try:
        with open(file_location, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > 10 * 1024 * 1024: # 10MB
                    f.close()
                    os.remove(file_location)
                    logger.error("Input file size exceeds 10MB limit.")
                    raise HTTPException(status_code=413, detail="Input file size exceeds 10MB limit.")
                f.write(chunk)
        logger.info(f"File '{unique_filename}' uploaded successfully for user '{username}'.")
        return unique_filename
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))

def get_download_file_path(username: str, filename: str, logger, agent_files_upload_dir):
    safe_username = "".join(c for c in username if c.isalnum() or c in ('-', '_')).lower()
    folder_name = os.path.join(agent_files_upload_dir, safe_username)
    safe_filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_', '.', '(', ')'))

    if not os.path.exists(folder_name):
        logger.error(f"Folder '{folder_name}' does not exist for user '{username}'.")
        raise HTTPException(status_code=404, detail="File not found")

    # Only allow exact filename match
    if safe_filename in os.listdir(folder_name):
        actual_filename = safe_filename
    else:
        logger.error(f"File '{filename}' not found for user '{username}'.")
        raise HTTPException(status_code=404, detail="File not found")

    file_location = os.path.join(folder_name, actual_filename)
    logger.info(f"File '{actual_filename}' found for user '{username}'.")
    return file_location


@router.post(
    "/Upload",
    summary="Upload File for Chat Agent",
    description="Uploads a file (up to 10MB) for a specific user. The file is stored in a user-specific directory with a unique filename.",
    operation_id="upload_file"
)
async def upload_file(
        file: UploadFile = File(...),
        json_data: str = Form(...),
        agent_files_upload_dir=Depends(get_agent_files_upload_dir),
        log_dir_path=Depends(get_log_dir_path)
):
    """
    Accepts a file and a JSON string (as 'json_data' form field).
    The client should send multipart/form-data with a 'file' and a 'json_data' field (json_data should be a JSON string).
    """
    logger = lg.configure_logger(f"{log_dir_path}/FileUpload")
    try:
        import json as pyjson
        try:
            data = pyjson.loads(json_data)
        except Exception as e:
            logger.error("Invalid JSON in 'json_data' field")
            raise HTTPException(status_code=400, detail="Invalid JSON in 'json_data' field")

        username = data.get("username")
        if not username:
            logger.error("Username is required in the JSON body.")
            raise HTTPException(status_code=400, detail="Username is required in the JSON body.")

        unique_filename = await async_save_uploaded_file(file, username, logger, agent_files_upload_dir)
        return {"filename": unique_filename, "status": "uploaded"}
    except Exception:
        raise
    finally:
        lg.shutdown_logger(logger)

@router.get(
    "/Download",
    summary="Download Uploaded File",
    description="Downloads a previously uploaded file for a specific user. Requires username and filename as query parameters.",
    operation_id="download_file"
)
async def download_file(
        username: str = Query(..., description="Username who uploaded the file"),
        filename: str = Query(..., description="Original filename uploaded by the user"),
        log_dir_path=Depends(get_log_dir_path),
        agent_files_upload_dir=Depends(get_agent_files_upload_dir)
):
    logger = lg.configure_logger(f"{log_dir_path}/FileDownload")
    try:
        if not username or not filename or filename.lower() == "null":
            logger.error("Invalid username or filename")
            raise HTTPException(status_code=400, detail="Invalid username or filename")

        file_location = get_download_file_path(username, filename, logger, agent_files_upload_dir)
        return FileResponse(path=file_location, filename=filename)
    finally:
        lg.shutdown_logger(logger)

@router.delete(
    "/Delete",
    summary="Delete Uploaded File",
    description="Deletes a previously uploaded file for a specific user. Requires username and filename as query parameters.",
    operation_id="delete_file"
)
async def delete_file(
        username: str = Query(..., description="Username who uploaded the file"),
        filename: str = Query(..., description="Original filename uploaded by the user"),
        log_dir_path=Depends(get_log_dir_path),
        agent_files_upload_dir=Depends(get_agent_files_upload_dir)
):
    logger = lg.configure_logger(f"{log_dir_path}/FileDelete")
    try:
        safe_username = "".join(c for c in username if c.isalnum() or c in ('-', '_')).lower()
        folder_name = os.path.join(agent_files_upload_dir, safe_username)
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_', '.', '(', ')'))

        if not os.path.exists(folder_name):
            logger.error(f"Folder '{folder_name}' does not exist for user '{username}'.")
            raise HTTPException(status_code=404, detail="File not found")

        if safe_filename in os.listdir(folder_name):
            file_location = os.path.join(folder_name, safe_filename)
            try:
                os.remove(file_location)
                logger.info(f"File '{safe_filename}' deleted for user '{username}'.")
                return {"status": "deleted", "filename": safe_filename}
            except Exception as e:
                logger.error(f"Error deleting file '{safe_filename}': {e}")
                raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")
        else:
            logger.error(f"File '{filename}' not found for user '{username}'.")
            raise HTTPException(status_code=404, detail="File not found")
    finally:
        lg.shutdown_logger(logger)
