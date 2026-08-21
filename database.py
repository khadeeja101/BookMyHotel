from flask_sqlalchemy import SQLAlchemy

# Creating the single global instance of the SQLAlchemy database manager
# Initialized in app.py, used throughout the application to interact with the database
db = SQLAlchemy()
