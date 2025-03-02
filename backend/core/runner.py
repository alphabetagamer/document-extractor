from langchain.callbacks import get_openai_callback
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import HumanMessage
from PIL import Image
import pdf2image
import os
import base64
from io import BytesIO
import json
from typing import Dict, List, Tuple, Any, Optional, Union
import logging
import traceback
import re
from pydantic import BaseModel, Field, create_model
from backend.models.api_models import APIConfig, ExtractionRequest
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_pdf_to_images(pdf_path: str) -> List[Image.Image]:
    """Convert PDF to list of PIL Images"""
    try:
        # Convert PDF to list of images
        images = pdf2image.convert_from_path(pdf_path, dpi=300)
        
        # If there's only one page, return it directly
        if len(images) <= 1:
            return images
            
        # Calculate dimensions for the combined image
        width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        
        # Create a new image with the combined dimensions
        combined_image = Image.new('RGB', (width, total_height))
        
        # Paste each page into the combined image
        y_offset = 0
        for img in images:
            combined_image.paste(img, (0, y_offset))
            y_offset += img.height
        
        # Return the combined image as a single-item list to maintain interface
        return [combined_image]
    except Exception as e:
        logger.error(f"Error converting PDF {pdf_path} at line {traceback.extract_tb(e.__traceback__)[-1].lineno}: {str(e)}")
        raise

def encode_image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string"""
    try:
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image at line {traceback.extract_tb(e.__traceback__)[-1].lineno}: {str(e)}")
        raise

def get_image_from_file(file_path: str) -> List[Image.Image]:
    """Get PIL Image(s) from file path"""
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext == '.pdf':
            return convert_pdf_to_images(file_path)  # Return all pages
        elif file_ext in ['.jpg', '.jpeg', '.png']:
            return [Image.open(file_path)]  # Return single image as a list
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    except Exception as e:
        logger.error(f"Error getting image from file {file_path}: {str(e)}")
        raise

def create_llm_client(api_config: APIConfig):
    """Create LLM client based on provider"""
    try:
        if api_config.provider.lower() == 'openai':
            return ChatOpenAI(
                model=api_config.model,
                api_key=api_config.api_key,
                max_tokens=api_config.max_tokens,
                temperature=api_config.temperature
            )
        elif api_config.provider.lower() == 'azure':
            if not api_config.azure_endpoint or not api_config.azure_deployment or not api_config.api_version:
                raise ValueError("Azure OpenAI requires endpoint, deployment name, and API version")
            
            return AzureChatOpenAI(
                azure_deployment=api_config.azure_deployment,
                openai_api_version=api_config.api_version,
                azure_endpoint=api_config.azure_endpoint,
                api_key=api_config.api_key,
                max_tokens=api_config.max_tokens,
                temperature=api_config.temperature
            )
        else:
            raise ValueError(f"Unsupported provider: {api_config.provider}")
    except Exception as e:
        logger.error(f"Error creating LLM client: {str(e)}")
        raise

def create_dynamic_model(schema_definition: Dict[str, Any]) -> BaseModel:
    """Create a dynamic Pydantic model from schema definition"""
    try:
        # Extract field definitions and their types
        fields = {}
        for field_name, field_def in schema_definition.items():
            field_type = field_def.get("type", Any)
            description = field_def.get("description", "")
            default = field_def.get("default", ...)
            
            # Handle nested properties
            if "properties" in field_def and isinstance(field_def["properties"], dict):
                # Create a nested model for this field
                nested_fields = {}
                for nested_field_name, nested_field_def in field_def["properties"].items():
                    nested_field_type = nested_field_def.get("type", Any)
                    nested_description = nested_field_def.get("description", "")
                    nested_default = nested_field_def.get("default", ...)
                    
                    # Convert string type names to actual types for nested fields
                    if isinstance(nested_field_type, str):
                        if nested_field_type.lower() == "string":
                            nested_field_type = str
                        elif nested_field_type.lower() in ["int", "integer"]:
                            nested_field_type = int
                        elif nested_field_type.lower() in ["float", "number"]:
                            nested_field_type = float
                        elif nested_field_type.lower() in ["bool", "boolean"]:
                            nested_field_type = bool
                        elif nested_field_type.lower() in ["list", "array"]:
                            nested_field_type = List[Any]
                        elif nested_field_type.lower() in ["dict", "object"]:
                            nested_field_type = Dict[str, Any]
                    
                    nested_fields[nested_field_name] = (nested_field_type, Field(nested_default, description=nested_description))
                
                # Create the nested model
                nested_model = create_model(f"{field_name.capitalize()}Model", **nested_fields)
                
                # Use the nested model as the field type
                field_type = nested_model
            else:
                # Convert string type names to actual types
                if isinstance(field_type, str):
                    if field_type.lower() == "string":
                        field_type = str
                    elif field_type.lower() in ["int", "integer"]:
                        field_type = int
                    elif field_type.lower() in ["float", "number"]:
                        field_type = float
                    elif field_type.lower() in ["bool", "boolean"]:
                        field_type = bool
                    elif field_type.lower() in ["list", "array"]:
                        field_type = List[Any]
                    elif field_type.lower() in ["dict", "object"]:
                        field_type = Dict[str, Any]
            
            fields[field_name] = (field_type, Field(default, description=description))
        
        # Create and return the dynamic model
        return create_model("DynamicExtractionModel", **fields)
    except Exception as e:
        logger.error(f"Error creating dynamic model: {str(e)}")
        raise

def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse LLM response text to extract JSON"""
    try:
        # First try direct JSON parsing
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            json_str = json_match.group(1).strip()
            return json.loads(json_str)
        
        # If still no valid JSON, try to clean up the response
        # Remove any non-JSON text before the first { and after the last }
        first_brace = response_text.find('{')
        last_brace = response_text.rfind('}')
        
        if first_brace != -1 and last_brace != -1:
            json_str = response_text[first_brace:last_brace+1]
            return json.loads(json_str)
        
        raise ValueError("Could not parse valid JSON from response")
    except Exception as e:
        logger.error(f"Error parsing LLM response: {str(e)}")
        raise

def extract_from_image(image: Image.Image, extraction_request: ExtractionRequest) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Extract data from image based on schema and prompt"""
    try:
        # Convert image to base64
        base64_image = encode_image_to_base64(image)
        
        # Create LLM client
        chat = create_llm_client(extraction_request.api_config)
        
        # Use provided prompt or generate a default one
        prompt_text = extraction_request.prompt
        if not prompt_text:
            # Generate default prompt based on schema if schema is provided
            if extraction_request.schema_definition:
                field_descriptions = []
                for field_name, field_def in extraction_request.schema_definition.items():
                    description = field_def.get("description", field_name)
                    field_descriptions.append(f"- {field_name}: {description}")
                
                schema_description = "\n".join(field_descriptions)
                prompt_text = f"""Extract the following information from the image and return it in JSON format:

{schema_description}

Return the data in valid JSON format matching the requested schema.
"""
            else:
                # Default prompt if no schema and no custom prompt provided
                prompt_text = """Extract all relevant information from this image and return it in a structured JSON format.
Make sure to include any key details given in the prompt.
Return your response as valid JSON."""
            
            # Truncate if too long
            if len(prompt_text) > 4000:
                prompt_text = prompt_text[:3997] + "..."
        else:
            prompt_text = "Extract the following information from the image and return it in JSON format: " + prompt_text
        # Create messages with image
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            )
        ]
        
        # Get response with cost tracking
        usage_metrics = {}
        with get_openai_callback() as cb:
            # If schema is provided, use Pydantic parser
            if extraction_request.schema_definition:
                dynamic_model = create_dynamic_model(extraction_request.schema_definition)
                parser = PydanticOutputParser(pydantic_object=dynamic_model)
                chain = chat | parser
                response = chain.invoke(messages)
                extracted_data = response.dict()
            else:
                # If no schema, just get raw response and parse it
                response = chat.invoke(messages)
                extracted_data = parse_llm_response(response.content)
            
            usage_metrics = {
                "prompt_tokens": cb.prompt_tokens,
                "completion_tokens": cb.completion_tokens,
                "total_tokens": cb.total_tokens,
                "total_cost": round(cb.total_cost, 4)
            }
        
        return extracted_data, usage_metrics

    except Exception as e:
        logger.error(f"Error extracting from image: {str(e)}")
        raise

def process_file(file_path: str, extraction_request: ExtractionRequest) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Process a single file and extract data according to the schema"""
    try:
        # Get images from file
        images = get_image_from_file(file_path)
        
        extracted_data_list = []
        usage_metrics_list = []
        total_cost = 0.0
        
        # Process each page/image
        for i, image in enumerate(images):
            logger.info(f"Processing page {i+1}/{len(images)} of {os.path.basename(file_path)}")
            
            # Extract data from image
            extracted_data, usage_metrics = extract_from_image(image, extraction_request)
            
            # Add filename and page number to usage metrics
            usage_metrics["file_name"] = os.path.basename(file_path)
            usage_metrics["page_number"] = i + 1
            
            # Track total cost
            total_cost += usage_metrics["total_cost"]
            
            extracted_data_list.append(extracted_data)
            usage_metrics_list.append(usage_metrics)
        
        # Create file-level metadata with total cost
        file_metadata = {
            "file_name": os.path.basename(file_path),
            "page_count": len(images),
            "page_metrics": usage_metrics_list,
            "total_cost": round(total_cost, 4)
        }
        
        return extracted_data_list, file_metadata
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        return [], {"file_name": os.path.basename(file_path), "error": str(e), "total_cost": 0.0}

def process_files(file_paths: List[str], extraction_request: ExtractionRequest) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Process multiple files and extract data according to the schema"""
    all_extracted_data = []
    all_file_metadata = []
    total_cost = 0.0
    
    for file_path in file_paths:
        try:
            logger.info(f"Processing {os.path.basename(file_path)}")
            data_list, file_metadata = process_file(file_path, extraction_request)
            
            if data_list:
                all_extracted_data.extend(data_list)
                all_file_metadata.append(file_metadata)
                total_cost += file_metadata.get("total_cost", 0.0)
            else:
                logger.warning(f"Failed to process {os.path.basename(file_path)}")
        except Exception as e:
            logger.error(f"Error processing {os.path.basename(file_path)}: {str(e)}")
            all_file_metadata.append({
                "file_name": os.path.basename(file_path),
                "error": str(e),
                "total_cost": 0.0
            })
    
    # Create overall metadata with total cost
    overall_metadata = {
        "files": all_file_metadata,
        "file_count": len(file_paths),
        "successful_extractions": len(all_extracted_data),
        "total_cost": round(total_cost, 4)
    }
    
    return all_extracted_data, overall_metadata

# Sample usage:
"""
# Example 1: Using schema-based extraction
from backend.models.api_models import APIConfig, ExtractionRequest

# Create API config
api_config = APIConfig(
    provider="openai",
    api_key="your-api-key",
    model="gpt-4o"
)

# Define schema
schema_definition = {
    "vendor_name": {"type": "string", "description": "Name of the vendor"},
    "invoice_date": {"type": "string", "description": "Date of the invoice"},
    "total_amount": {"type": "float", "description": "Total invoice amount"}
}

# Create extraction request with schema
extraction_request = ExtractionRequest(
    api_config=api_config,
    schema_definition=schema_definition,
    prompt="Extract invoice details from this image"
)

# Process files
file_paths = ["invoice1.pdf", "invoice2.jpg"]
data, usage = process_files(file_paths, extraction_request)

# Example 2: Using prompt-only extraction (no schema)
prompt_only_request = ExtractionRequest(
    api_config=api_config,
    schema_definition={},  # Empty schema
    prompt="Extract all relevant invoice information and return as JSON"
)

# Process files with prompt-only extraction
data, usage = process_files(file_paths, prompt_only_request)
"""
