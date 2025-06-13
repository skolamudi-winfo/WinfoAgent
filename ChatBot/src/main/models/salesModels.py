from pydantic import BaseModel


class SalesChatRequest(BaseModel):
    question: str
    session_id: str
    query_level: str
    user_name: str
    chat_id: str
    product_name: str
