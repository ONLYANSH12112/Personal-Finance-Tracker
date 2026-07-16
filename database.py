import os

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        import psycopg2
        return psycopg2.connect(database_url)

    import mysql.connector
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="tiger23",
        database="finance_tracker"
    )