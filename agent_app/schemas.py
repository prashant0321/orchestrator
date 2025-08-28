from pydantic import BaseModel, EmailStr
from typing import Dict, List, Any, Optional
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class StageMode(str, Enum):
    DETERMINISTIC = "deterministic"
    NON_DETERMINISTIC = "non_deterministic"

class MCPServer(str, Enum):
    ATLAS = "atlas"
    COMMON = "common"

class CustomerSupportInput(BaseModel):
    customer_name: str
    customer_email: EmailStr
    query: str
    priority: Priority = Priority.MEDIUM
    ticket_id: Optional[str] = None

class AgentState(BaseModel):
    ticket_id: str
    customer_name: str
    customer_email: str
    original_query: str
    priority: str
    
    # Stage-specific data
    parsed_request: Optional[Dict[str, Any]] = None
    extracted_entities: Optional[Dict[str, Any]] = None
    normalized_fields: Optional[Dict[str, Any]] = None
    enriched_data: Optional[Dict[str, Any]] = None
    clarification_needed: Optional[bool] = None
    customer_answer: Optional[str] = None
    knowledge_base_results: Optional[List[Dict]] = None
    solution_score: Optional[float] = None
    escalation_required: Optional[bool] = None
    response_text: Optional[str] = None
    api_results: Optional[Dict[str, Any]] = None
    final_payload: Optional[Dict[str, Any]] = None
    
    # Workflow metadata
    current_stage: str = "INTAKE"
    stage_logs: List[Dict[str, Any]] = []
    errors: List[str] = []

class StageConfig(BaseModel):
    name: str
    mode: StageMode
    abilities: List[str]
    mcp_server: MCPServer
    prompt_template: str
    next_stage: Optional[str] = None
    condition_field: Optional[str] = None
