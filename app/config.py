from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    environment: str = "development"
    workos_api_key: str
    workos_client_id: str
    workos_redirect_uri: str
    frontend_url: str = "http://localhost:5500"
    paystack_secret_key: str
    cron_secret_key: str
    redis_url: str
    brevo_login: str
    brevo_smtp_key: str
    email_sender: str

    class Config:
        env_file = ".env"

settings = Settings()