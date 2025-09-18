from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "SelfOrderM"
    API_V1: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    DATABASE_URL: str = "postgresql+asyncpg://selforder:selforder@localhost:5432/selforder"
    JWT_SECRET: str = "dev-secret"
    JWT_ALG: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()
