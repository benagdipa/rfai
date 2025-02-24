import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost/network_db")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "/path/to/credentials.json")
    AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "your-airtable-key")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key")

settings = Settings()
