import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-change-me'
    DB_PATH    = os.environ.get('DB_PATH', '/data/notes.db')
    API_KEY    = os.environ.get('API_KEY', '')
    FEED_TITLE = os.environ.get('FEED_TITLE', 'CCFeed')
