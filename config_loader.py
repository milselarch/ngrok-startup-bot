from enum import Enum

from pydantic import BaseModel, validator

class Config(BaseModel):
    bot_token: str
    chat_id: str
