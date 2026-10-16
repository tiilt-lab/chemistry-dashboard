# Creates a user with a specified username, role, and password.
#
# Run from src/server with the server's venv:
#     ../venv-server/bin/python create_user.py
#
# Flask-SQLAlchemy 3 only hands out a database session inside an application
# context, so the write runs under app.app_context(); without it the script
# failed with "Working outside of application context" before saving anything,
# which left a fresh install with no way to sign in.

import database
from app import app

if __name__ == '__main__':
    print('Username:')
    username = input()
    print('Password:')
    password = input()
    print('Input role:')
    print('1 - User')
    print('2 - Admin')
    print('3 - Super')
    role_index = input()
    role = 'user'
    if role_index == '2':
        role = 'admin'
    elif role_index == '3':
        role = 'super'
    with app.app_context():
        print(database.add_user(username, role=role, password=password))
        database.close_session()
