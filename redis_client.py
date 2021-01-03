import redis


class RedisClient:
    
    def __init__(self, user=None, password=None, host='localhost', port=6379, db=0):
        self._conn = redis.Redis(host=host, port=port, db=db)
    
    def set(self, k, v):
        self._conn.set(k, v)
    
    def get(self, k):
        return self._conn.get(k)
