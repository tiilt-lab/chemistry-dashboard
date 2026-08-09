"""Cross-process claim primitive (architecture fix #6).

Coordination like "is this pod already being processed?" was an in-process
dict guarded by a threading.Lock. That serializes THREADS within one process,
but says nothing to a second process (or a future second instance) — the
architecture silently assumed exactly one process per role, forever.

This is the missing shared primitive: an atomic claim in Redis (SET key NX EX),
so at most one holder across all processes. Two properties make adopting it
low-risk:

  * In-memory fallback. If Redis is unreachable (or unconfigured), it degrades
    to a per-process dict — i.e. exactly today's behavior. Never worse.
  * A TTL on every claim. A holder that dies without releasing self-heals when
    the TTL expires, instead of wedging the pod forever (the in-process dict
    never expired — that was a real bug class this session).

The Redis client is injected (``redis_factory``) so the primitive is unit
testable without a server, and so callers can share the process's existing
connection.
"""
import logging
import threading


class DistributedClaim:
    def __init__(self, redis_factory=None, prefix="claim:"):
        # redis_factory: callable returning a redis client, or None for a pure
        # in-memory claim (single-process). A factory that raises is treated
        # as "Redis unavailable" and falls back to memory.
        self._redis_factory = redis_factory
        self._prefix = prefix
        self._mem = {}
        self._lock = threading.Lock()
        self._warned = False

    def _redis(self):
        if self._redis_factory is None:
            return None
        try:
            return self._redis_factory()
        except Exception as e:
            self._warn(e)
            return None

    def _warn(self, e):
        if not self._warned:
            self._warned = True
            logging.warning("DistributedClaim: Redis unavailable, using "
                            "in-memory (single-process) fallback: %s", e)

    def try_claim(self, key, ttl=3600):
        """Atomically claim ``key``. True if acquired, False if already held.
        The claim auto-expires after ``ttl`` seconds so a dead holder can't
        wedge the resource permanently."""
        r = self._redis()
        if r is not None:
            try:
                # SET NX EX: set-if-absent with expiry, in one atomic op.
                return bool(r.set(self._prefix + key, "1", nx=True, ex=ttl))
            except Exception as e:
                self._warn(e)  # fall through to the in-memory path
        with self._lock:
            if key in self._mem:
                return False
            self._mem[key] = True
            return True

    def release(self, key):
        r = self._redis()
        if r is not None:
            try:
                r.delete(self._prefix + key)
            except Exception as e:
                self._warn(e)  # TTL will clear it regardless
        with self._lock:
            self._mem.pop(key, None)

    def is_claimed(self, key):
        r = self._redis()
        if r is not None:
            try:
                return bool(r.exists(self._prefix + key))
            except Exception as e:
                self._warn(e)
        with self._lock:
            return key in self._mem
