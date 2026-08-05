import sys
import database
import re

if __name__ == '__main__':
    print(database.add_user(sys.argv[1].split('@')[0], role=sys.argv[2], password=sys.argv[1].split('@')[1]))
    database.close_session()
