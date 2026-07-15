import os

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render (PostgreSQL)
    import psycopg2

    def get_db_connection():
        return psycopg2.connect(DATABASE_URL)

else:
    # Local VS Code (MySQL)
    import mysql.connector

    def get_db_connection():
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="tiger23",
            database="finance_tracker"
        )