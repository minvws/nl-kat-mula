from pydantic import BaseSettings


class Settings(BaseSettings):
    DEBUG: bool = False
