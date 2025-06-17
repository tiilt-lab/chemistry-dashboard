import redis
import time
import json
import logging

r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

class RedisLogin:
    EXPIRATION_TIME = 60 * 5
    MAX_FAILED_ATTEMTPS = 5

    @staticmethod
    def make_redis_key(email, ip):
        return '{0}-{1}'.format(email, ip)

    @staticmethod
    def failed_login_attempt(email, ip):
        redis_key = RedisLogin.make_redis_key(email, ip)
        r.lpush(redis_key, time.time())
        r.expireat(redis_key, int(time.time() + RedisLogin.EXPIRATION_TIME))

    @staticmethod
    def successful_login_attempt(email, ip):
        redis_key = RedisLogin.make_redis_key(email, ip)
        r.delete(redis_key)

    @staticmethod
    def can_login(email, ip):
        cur_time = time.time() - RedisLogin.EXPIRATION_TIME
        redis_key = RedisLogin.make_redis_key(email, ip)
        if not r.exists(redis_key):
            return True
        all_times = r.lrange(redis_key, 0, r.llen(redis_key))
        failed_times = [t for t in all_times if float(t) >= cur_time]
        return len(failed_times) < RedisLogin.MAX_FAILED_ATTEMTPS

    @staticmethod
    def unlock_login(email):
        keys = []
        for key in r.scan_iter(match='{0}*'.format(email)):
            keys.append(key)
        if len(keys) > 0:
            r.delete(*keys)

class RedisSessions:

    @staticmethod
    def make_config_redis_key(session_id):
        return 'APS-Config-{0}'.format(session_id)

    @staticmethod
    def make_auth_redis_key(processing_key):
        return 'APS-Auth-{0}'.format(processing_key)

    @staticmethod
    def create_session(session_id, config):
        redis_key = RedisSessions.make_config_redis_key(session_id)
        r.set(redis_key, json.dumps(config))

    @staticmethod
    def get_session(session_id):
        redis_key = RedisSessions.make_config_redis_key(session_id)
        return r.get(redis_key)

    @staticmethod
    def delete_session(session_id):
        redis_key = RedisSessions.make_config_redis_key(session_id)
        r.delete(redis_key)

    @staticmethod
    def create_device_key(processing_key, session_id):
        redis_auth_key = RedisSessions.make_auth_redis_key(processing_key)
        redis_config_key = RedisSessions.make_config_redis_key(session_id)
        r.set(redis_auth_key, redis_config_key)

    @staticmethod
    def get_device_key(processing_key):
        redis_key = RedisSessions.make_auth_redis_key(processing_key)
        return r.get(redis_key)

    @staticmethod
    def delete_device_key(processing_key):
        redis_key = RedisSessions.make_auth_redis_key(processing_key)
        r.delete(redis_key)

    @staticmethod
    def get_session_config(redis_key):
        return r.get(redis_key)


if __name__ == '__main__':
    data = None
    while data != 'q':
        data = input()
        if data == '1':
            RedisLogin.failed_login_attempt('bob', '123.456')
        elif data == '2':
            RedisLogin.successful_login_attempt('bob', '123.456')
        elif data == '3':
            print(RedisLogin.can_login('bob', '123.456'))
        elif data == '4':
            RedisLogin.unlock_login('bob')
        elif data == '5':
            floats = r.lrange('bob-123.456', 0, r.llen('bob-123.456'))
            print(floats)