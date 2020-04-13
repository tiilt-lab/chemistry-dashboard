# Creates a user with a specified username, role, and password.

import database

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
    print(database.add_user(username, role=role, password=password))
    database.close_session()