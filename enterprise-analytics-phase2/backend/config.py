from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
   # Google Cloud
   GCP_PROJECT_ID: str = "vf-grp-gbissdbx-dev-1"
   GCP_LOCATION: str = "us-central1"
   # Vertex AI
   VERTEX_AI_MODEL: str = "gemini-2.5-flash-lite"
   VERTEX_AI_TEMPERATURE: float = 0.2
   VERTEX_AI_MAX_TOKENS: int = 2048
   # BigQuery
   BIGQUERY_DATASET: str = "KarthikRudrapati"
   BIGQUERY_LOCATION: str = "US"
   # Security
   SECRET_KEY: str = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6"
   ALGORITHM: str = "HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
   # CORS
   ALLOWED_ORIGINS: List[str] = [
       "http://localhost:5173",
       "http://localhost:8000"
   ]
   # App
   LOG_LEVEL: str = "INFO"
   ENVIRONMENT: str = "development"
   model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()