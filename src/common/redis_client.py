import redis
import config as cf

# Created lazily: this module is imported before cf.initialize() runs,
# so config values are not available at import time.
_r = None

def _redis():
    global _r
    if _r is None:
        _r = redis.StrictRedis(host=cf.redis_host(), port=cf.redis_port(), db=cf.redis_db(), decode_responses=True)
    return _r

class RedisSessions:

    @staticmethod
    def make_config_redis_key(session_id):
        return 'APS-Config-{0}'.format(session_id)

    @staticmethod
    def make_auth_redis_key(processing_key):
        return 'APS-Auth-{0}'.format(processing_key)

    @staticmethod
    def get_session_config(redis_key):
        return _redis().get(redis_key)

    @staticmethod
    def get_device_key(processing_key):
        redis_key = RedisSessions.make_auth_redis_key(processing_key)
        return _redis().get(redis_key)
