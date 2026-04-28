from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "shortlink"
    dynamodb_table: str = "shortlink-links"
    aws_region: str = "ap-northeast-1"
    base_url: str = "https://shortlink"
    code_length: int = 7
    dynamodb_endpoint_url: str | None = None  # set to http://localhost:8000 for DynamoDB Local

    class Config:
        env_file = ".env"


settings = Settings()
