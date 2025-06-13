from pydantic import BaseModel


class MessageFeedback(BaseModel):
    chat_id: str
    message_id: int
    feedback: dict


class ChatResponse(BaseModel):
    chat_id: str
    message_id: int


