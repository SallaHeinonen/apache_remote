import csv
import hashlib
import random
import string
import mysql.connector
import smtplib
from email.mime.text import MIMEText
from mysql.connector import Error

# Constants
CSV_PATH = '/opt/python/users.csv'

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3307,
    'database': 'guacamole_db',
    'user': 'pythonadmin',
    'password': 'secretpass'
}

# For the test demonstration, a gmail address was created and used for sending the emails.

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'tensorflowserverproject@gmail.com'
SMTP_PASS = 'ksdi nkgz vdmi mpcc'
EMAIL_FROM = SMTP_USER


def generate_password(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def sha256(password):
    return hashlib.sha256(password.encode()).digest()  # Binary hash for Guacamole


# Mail generation 

def send_email(recipient, password):
    body = f"""You have been given an account for the Tensorflow's remote access system.
n\Your temporary password for Apache Guacamole remote access is: {password}
\nPlease change your password after logging in. \nUse this email address for login.
\nThis is an automated message."""
    msg = MIMEText(body)
    msg['Subject'] = 'Login details for Guacamole'
    msg['From'] = EMAIL_FROM
    msg['To'] = recipient
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, [recipient], msg.as_string())

# User creation for the database

def create_user(email, db_conn):
    cursor = db_conn.cursor()

    # Check if user (entity) exists
    cursor.execute("SELECT entity_id FROM guacamole_entity WHERE name = %s AND type = 'USER'", (email,))
    if cursor.fetchone():
        print(f"[!] User {email} already exists.")
        return

    password = generate_password()
    hashed_pw = sha256(password)

    
    # Insert into guacamole_entity to create the entity first
    cursor.execute("""
        INSERT INTO guacamole_entity (name, type)
        VALUES (%s, 'USER')
    """, (email,))
    db_conn.commit()

    # Get the entity_id for the newly created user
    cursor.execute("SELECT entity_id FROM guacamole_entity WHERE name = %s AND type = 'USER'", (email,))
    entity_id = cursor.fetchone()[0]

    # Insert into guacamole_user with the entity_id
    cursor.execute("""
        INSERT INTO guacamole_user (
            entity_id, password_hash, password_salt, password_date, 
            full_name, email_address
        ) VALUES (
            %s, %s, NULL, NOW(),
            %s, %s
        )
    """, (entity_id, hashed_pw, email.split('@')[0], email))
    db_conn.commit()

    # Get the user_id for the same user
    cursor.execute("SELECT user_id FROM guacamole_user WHERE entity_id = %s", (entity_id,))
    user_id = cursor.fetchone()[0]

    # Grant the user permission to change their own password (via the user permission)
    cursor.execute("""
        INSERT INTO guacamole_user_permission (entity_id, affected_user_id, permission)
        VALUES (%s, %s, 'UPDATE')
    """, (entity_id, user_id))
    db_conn.commit()
    
    print(f"[+] Created user {email} with temporary password: {password}")
    send_email(email, password)


def main():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("[+] Connected to MySQL with assigned adminuser!")

            with open(CSV_PATH, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    email = row['email'].strip()
                    if email:
                        create_user(email, connection)

    except Error as e:
        print(f"[X] MySQL connection error: {e}")

    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("[+] MySQL connection closed.")


if __name__ == '__main__':
    main()