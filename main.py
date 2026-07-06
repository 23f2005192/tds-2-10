from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import time
from collections import defaultdict

EMAIL = "23f2005192@ds.study.iitm.ac.in"

ALLOWED_ORIGINS = [
    "https://app-sc6wzi.example.com",
]

# Add the exam page origin if required by the grader
# Example:
# ALLOWED_ORIGINS.append("https://exam.sanand.workers.dev")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

WINDOW = 10
LIMIT = 13

requests = defaultdict(list)


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("X-Request-ID")
    if not rid:
        rid = str(uuid4())

    request.state.request_id = rid

    response = await call_next(request)

    response.headers["X-Request-ID"] = rid

    return response


@app.middleware("http")
async def rate_limit(request: Request, call_next):

    client = request.headers.get("X-Client-Id", "default")

    now = time.time()

    requests[client] = [
        t for t in requests[client]
        if now - t < WINDOW
    ]

    if len(requests[client]) >= LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

    requests[client].append(now)

    return await call_next(request)


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }