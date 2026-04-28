from pydantic import BaseModel, HttpUrl, field_validator


class CreateLinkRequest(BaseModel):
    url: HttpUrl
    custom_code: str | None = None

    @field_validator("custom_code")
    @classmethod
    def code_must_be_alphanumeric(cls, v: str | None) -> str | None:
        if v is not None and not v.isalnum():
            raise ValueError("custom_code must be alphanumeric")
        if v is not None and (len(v) < 3 or len(v) > 20):
            raise ValueError("custom_code must be 3–20 characters")
        return v


class LinkResponse(BaseModel):
    code: str
    url: str
    short_url: str
    created_at: str
    hits: int = 0


class StatsResponse(BaseModel):
    code: str
    url: str
    short_url: str
    created_at: str
    hits: int
