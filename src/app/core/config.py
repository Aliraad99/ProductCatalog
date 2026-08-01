from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    REQUEST_ID_HEADER: str = "X-Request-ID"

    class Config:
        env_file = ".env"

settings = Settings()