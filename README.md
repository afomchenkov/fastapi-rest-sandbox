# FastAPI REST Sandbox


## Start the app:
```
docker-compose up --build
```

> running at: http://0.0.0.0:8000

```
.> app:         tasks:0x7f618d174fd0
.> transport:   redis://redis:6379/0
.> results:     postgresql://user:**@database:5432/alpha
.> concurrency: 8 (prefork)
.> task events: OFF (enable -E to monitor tasks in this worker)
```

## Links:
asyncio Redis: https://pypi.org/project/asyncio-redis/
redis-py Redis: https://github.com/redis/redis-py
redis-py docs: https://redis-py.readthedocs.io/en/stable/index.html
Redis commands: https://redis.io/docs/latest/commands/ts.create/
