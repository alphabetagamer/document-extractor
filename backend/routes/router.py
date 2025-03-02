from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import json
import os
from pydantic import BaseModel, Field
import tempfile
import shutil
import logging
import traceback
from backend.core.runner import (
    process_files
)
from backend.models.api_models import APIConfig, ExtractionRequest, ExtractResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()



@router.post("/extract/files", response_model=ExtractResponse)
async def extract_from_files(
    files: List[UploadFile] = File(...),
    api_provider: str = Form(...),
    api_key: str = Form(...),
    model: str = Form("gpt-4o"),
    max_tokens: int = Form(2048),
    temperature: float = Form(0.3),
    prompt: Optional[str] = Form(None),
    schema_definition: Optional[str] = Form(None),
    api_version: Optional[str] = Form(None),
    azure_endpoint: Optional[str] = Form(None),
    azure_deployment: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Extract data from multiple files using the provided schema"""
    try:
        # Parse schema definition if provided
        schema_def = json.loads(schema_definition) if schema_definition else None
        # Create API config
        api_config = APIConfig(
            provider=api_provider,
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            azure_deployment=azure_deployment
        )
        
        # Create extraction request
        extraction_request = ExtractionRequest(
            api_config=api_config,
            prompt=prompt,
            schema_definition=schema_def
        )
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        file_paths = []
        
        # Check file types and save valid files to temp location
        supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
        for file in files:
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in supported_extensions:
                logger.warning(f"Skipping unsupported file type: {file.filename}")
                continue
                
            temp_file_path = os.path.join(temp_dir, file.filename)
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_paths.append(temp_file_path)
            logger.info(f"Saved file for processing: {file.filename}")
        
        if not file_paths:
            raise HTTPException(status_code=400, detail="No valid PDF or image files were uploaded")
        
        # Process files
        data, usage = process_files(file_paths, extraction_request)
        
        # Clean up temp files in background
        background_tasks.add_task(shutil.rmtree, temp_dir)
        return ExtractResponse(data=data, usage=usage)
    
    except Exception as e:
        logger.error(f"Error in extract_from_files at line {traceback.extract_tb(e.__traceback__)}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

"""
Sample request body for /extract/files endpoint:

curl -X 'POST' \
  'http://localhost:8000/extract/files' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@invoice1.pdf' \
  -F 'files=@invoice2.jpg' \
  -F 'api_provider=openai' \
  -F 'api_key=sk-your-api-key' \
  -F 'model=gpt-4o' \
  -F 'max_tokens=2048' \
  -F 'temperature=0.3' \
  -F 'schema_definition={
    "vendor_name": "str",
    "invoice_number": "str",
    "invoice_date": "str",
    "invoice_total": "float",
    "product_names": "List[str]",
    "product_prices": "List[float]",
    "product_quantities": "List[int]"
  }'
"""
