from pydantic import BaseModel


class SupportChatRequest(BaseModel):
    user_message: str
    session_id: str
    chat_id: str
    user_name: str
    issue_id: str
    customer_name: str
    product_name: str
