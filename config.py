from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    default_calendar_id: str
    
    # Email settings (optional)
    email_host: Optional[str] = "smtp.gmail.com"
    email_port: Optional[int] = 465
    email_username: Optional[str] = None
    email_password: Optional[str] = None

    # Recipient settings
    email_subject: Optional[str] = "Weekly Calendar Events"
    recipient_emails: Optional[str] = None  # Comma-separated emails
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create settings instance
settings = Settings()
#