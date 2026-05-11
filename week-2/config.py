import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


class Config:
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "admin")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "secret")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "classicmodels")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))

    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


config = Config()