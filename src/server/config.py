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
    return domains()[0]

def domains():
    # 'domain' accepts a comma-separated list so one instance can serve
    # several hostnames (all must be allowed as SocketIO CORS origins).
    scheme = 'https' if https() else 'http'
    value = str(config['server']['domain'])
    return ['{0}://{1}'.format(scheme, d.strip()) for d in value.split(',') if d.strip()]

# Temp field until we implement RDS.
def database_user():
    user = str(config['server']['database_user'])
    return "{0}:{1}".format(user, user)

def database_name():
    return str(config['server'].get('database_name', 'discussion_capture'))

def root_dir():
    return str(config['rootpath']['root_dir'])

def redis_host():
    return str(config['server'].get('redis_host', 'localhost'))

def redis_port():
    return int(config['server'].get('redis_port', 6379))

def redis_db():
    # Defaults to 0 so existing deployments are unchanged. Set to a distinct
    # value per instance to isolate Redis keys + the SocketIO message queue.
    return int(config['server'].get('redis_db', 0))

def redis_url():
    return 'redis://{0}:{1}/{2}'.format(redis_host(), redis_port(), redis_db())