from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "OT Sentinel"
    aws_region: str = "ap-northeast-1"
    users_table: str = "otsentinel-prod-users"
    devices_table: str = "otsentinel-prod-devices"
    incidents_table: str = "otsentinel-prod-incidents"
    audit_table: str = "otsentinel-prod-audit"
    metrics_table: str = "otsentinel-prod-metrics"
    jwt_secret: str = "dev-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    dynamodb_endpoint_url: str | None = None
    sns_topic_arn: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
