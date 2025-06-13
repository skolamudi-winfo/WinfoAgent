from pydantic import BaseModel
from typing import List, Optional, Literal


class PromptConfig(BaseModel):
    agent_prompt_id: int
    system_instruction: str
    response_schema: Optional[dict] = None
    input_prompt: Optional[str] = None
    prompt_level: str
    customer: str
    llm_model_name: str
    llm_server_location: str
    prompt_created_by: str
    prompt_last_updated_by: Optional[str] = None
    nearest_neighbours: Optional[int] = None
    comments: Optional[str] = None
    product_name: str
    operation_flag: Literal[
        "I", "U", "D",
        "Insert", "Update", "Delete",
        "i", "u", "d",
        "insert", "update", "delete",
        "INSERT", "UPDATE", "DELETE"
    ]


class PromptConfigList(BaseModel):
    prompts: List[PromptConfig]


class ProcessDetails(BaseModel):
    description: str
    flow: str


class ProcessDetailsConfig(BaseModel):
    customer_process_detail_id: int
    customer_name: str
    process_name: str
    subprocess: Optional[str] = None
    process_details: ProcessDetails
    product_name: str
    operation_flag: Literal[
        "I", "U", "D",
        "Insert", "Update", "Delete",
        "i", "u", "d",
        "insert", "update", "delete",
        "INSERT", "UPDATE", "DELETE"
    ]


class ProcessDetailsConfigList(BaseModel):
    process_details: List[ProcessDetailsConfig]
