from pydantic import BaseSettings

class Settings(BaseSettings):
    NAVER_CLIENT_ID: str
    NAVER_CLIENT_SECRET: str
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()