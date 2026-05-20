from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import redis
import os
import hashlib
import time

app = FastAPI(title="URL Shortener")

def read_secret(name: str, fallback_env: str = None) -> str:
    """Read secret from file first, fall back to env var."""
    secret_path = f"/run/secrets/{name}"
    if os.path.exists(secret_path):
        with open(secret_path) as f:
            return f.read().strip()
    if fallback_env:
        return os.getenv(fallback_env, "")
    return ""

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", None),
    decode_responses=True
)

class URLRequest(BaseModel):
    url: str

def make_short_code(url: str) -> str:
    unique = f"{url}{time.time()}"
    return hashlib.md5(unique.encode()).hexdigest()[:6]

@app.get("/health")
def health():
    try:
        r.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="Redis unavailable")

@app.post("/shorten")
def shorten(req: URLRequest):
    code = make_short_code(req.url)
    r.hset(f"url:{code}", mapping={"url": req.url, "clicks": 0})
    return {"short_code": code, "short_url": f"/r/{code}"}

@app.get("/r/{code}")
def redirect(code: str):
    data = r.hgetall(f"url:{code}")
    if not data:
        raise HTTPException(status_code=404, detail="Short URL not found")
    r.hincrby(f"url:{code}", "clicks", 1)
    return RedirectResponse(url=data["url"])

@app.get("/stats/{code}")
def stats(code: str):
    data = r.hgetall(f"url:{code}")
    if not data:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return {"short_code": code, "url": data["url"], "clicks": data["clicks"]}

@app.get("/")
def root():
    return {"message": "URL Shortener running", "docs": "/docs"}