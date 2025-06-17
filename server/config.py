import configparser
import os

def initialize():
    global config
    config_path = os.path.dirname(os.path.abspath(__file__)) + '/config.ini'
    config = configparser.RawConfigParser(allow_no_value=True)
    config.read(config_path)

def https():
    return str(config['server']['https']) in ['true', 'True', 't']

def cloud():
    # TODO: probably want this as a separate config, but for now http/https is probably good enough
    # to determine if running in AWS
    return https()

def debug():
    return str(config['server']['debug']) in ['true', 'True', 't']

def domain():
    domain = str(config['server']['domain'])
    return '{0}://{1}'.format('https' if https() else 'http', domain)

# Temp field until we implement RDS.
def database_user():
    user = str(config['server']['database_user'])
    return "{0}:{1}".format(user, user)