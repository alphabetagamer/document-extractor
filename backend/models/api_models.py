from pydantic import BaseModel, Field, create_model
from typing import Dict, Any, Optional, List
class APIConfig(BaseModel):
    """Configuration for API credentials"""
    provider: str = Field(..., description="API provider: 'openai' or 'azure'")
    api_key: str = Field(..., description="API key for authentication")
    model: str = Field("gpt-4o", description="Model to use for extraction")
    # Azure specific fields
    api_version: Optional[str] = Field(None, description="API version for Azure")
    azure_endpoint: Optional[str] = Field(None, description="Azure endpoint URL")
    azure_deployment: Optional[str] = Field(None, description="Azure deployment name")
    # Common parameters
    max_tokens: int = Field(2048, description="Maximum tokens for completion")
    temperature: float = Field(0.3, description="Temperature for generation")

class ExtractionRequest(BaseModel):
    """Request model for extraction"""
    api_config: APIConfig
    prompt: Optional[str] = Field(None, description="Custom prompt limited to 4000 characters")
    schema_definition: Optional[Dict[str, Any]] = Field(None, description="Pydantic schema definition")
    
class ExtractResponse(BaseModel):
    """Response model for extraction endpoints"""
    data: Any = Field(..., description="Extracted data")
    usage: Dict[str, Any] = Field(..., description="Extraction metadata including cost and file information")