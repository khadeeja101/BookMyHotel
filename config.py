import os
from dotenv import load_dotenv

# Load environment variables from the .env file located in the project root
load_dotenv()

class Config:
    """
    Configuration class to manage application settings.
    It reads environment variables from the system or the .env file.
    """
    # Secret key for encrypting sessions and cookies, fallback to a secure hardcoded string
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bookmyhotel_secret_key_1029384756!')

    # Database Configuration:
    # We retrieve the DATABASE_URL (MySQL connection string) configured in the .env file.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("DATABASE_URL environment variable is required and must be configured for MySQL.")

    # Disable tracking modifications to save system overhead resources
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SMTP Configuration for Google Mail:
    # Set up email server parameters using standard variables
    MAIL_SERVER = os.environ.get('MAIL_SERVER', os.environ.get('SMTP_HOST', 'smtp.gmail.com'))
    MAIL_PORT = int(os.environ.get('MAIL_PORT', os.environ.get('SMTP_PORT', 587)))
    # We use TLS (typically port 587) for secure connection
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ['true', '1', 'yes']
    
    # Mail credentials loaded from the .env file
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', os.environ.get('SMTP_USER'))
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', os.environ.get('SMTP_PASSWORD'))
    
    # Default sender if none is specified in mail dispatch
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('SMTP_FROM', MAIL_USERNAME))
