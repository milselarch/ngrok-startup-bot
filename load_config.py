from typing import Optional
from pydantic import BaseModel, Field
from pydantic_yaml import parse_yaml_raw_as


class TelegramConfig(BaseModel):
    bot_token: str
    allowed_chat_ids: Optional[list[int]] = Field(default_factory=list)


class Config(BaseModel):
    telegram: TelegramConfig


def load_config(config_path: str = 'config.yml') -> Config:
    with open(config_path, 'r') as config_file_obj:
        raw_data = config_file_obj.read()
        yaml_config = parse_yaml_raw_as(Config, raw_data)
        return yaml_config
