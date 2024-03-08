from sqlalchemy import create_engine 
import sqlite3


def initialize_engine():
    engine = create_engine("sqlite:///period_tracker.db")
    return engine




def get_db_connection():
    """Get a connection to the database that can be used with the Flask app"""
    conn = sqlite3.connect("period_tracker.db")
    conn.row_factory = sqlite3.Row
    return conn
