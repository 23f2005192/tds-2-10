from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from collections import defaultdict
import time

app = FastAPI()

EMAIL = "23f2005192@ds.study.iitm.ac.in"

# Add BOTH your assigned origin and the exam page origin.
# Replace the second URL with the actual origin of the exam page.
ALLOWED_ORIGINS = [
    "https://app-sc6wzi.example.com",
    # "https://<exam-page-origin>",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

WINDOW = 10          # seconds
LIMIT = 13           # requests per window

client_requests = defaultdict(list)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    client_id = request.headers.get("X-Client-Id", "default")
    now = time.time()

    # Remove timestamps older than the window
    client_requests[client_id] = [
        t for t in client_requests[client_id]
        if now - t < WINDOW
    ]

    # Enforce limit
    if len(client_requests[client_id]) >= LIMIT:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())

        response = JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded"
            }
        )

        response.headers["X-Request-ID"] = request_id
        return response

    client_requests[client_id].append(now)

    return await call_next(request)


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }
