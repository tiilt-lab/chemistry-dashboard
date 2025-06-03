import redis
import config as cf

r = redis.StrictRedis(host="blinc-scrzmn.serverless.use2.cache.amazonaws.com", port=6379, db=0, decode_responses=True)

class RedisSessions:

    @staticmethod
    def make_config_redis_key(session_id):
        return 'APS-Config-{0}'.format(session_id)

    @staticmethod
    def make_auth_redis_key(processing_key):
        return 'APS-Auth-{0}'.format(processing_key)

    @staticmethod
    def get_session_config(redis_key):
        return r.get(redis_key)

    @staticmethod
    def get_device_key(processing_key):
        redis_key = RedisSessions.make_auth_redis_key(processing_key)
        return r.get(redis_key)
