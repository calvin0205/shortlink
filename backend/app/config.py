from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "shortlink"
    dynamodb_table: str = "shortlink-links"
    aws_region: str = "ap-northeast-1"
    base_url: str = "https://localhost:8000"
    code_length: int = 7

    class Config:
        env_file = ".env"


settings = Settings()
