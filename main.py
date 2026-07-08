from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict
from uuid import uuid4
import time
import os

# Initialize FastAPI app
app = FastAPI()

# Your assigned email
EMAIL = "23f2005192@ds.study.iitm.ac.in"

# CORS Configuration - Allowed origins
ALLOWED_ORIGINS = [
    "https://app-sc6wzi.example.com",      # Assigned origin
    "https://exam.sanand.workers.dev",     # Exam page origin
    "https://tds-2-10-5t2f.onrender.com"   # Your deployed service (for testing)
]

# Add CORS Middleware (must be first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],  # Expose custom header to client
)

# Rate limiting configuration
WINDOW_SECONDS = 10
REQUEST_LIMIT = 13

# Store client request timestamps
client_requests = defaultdict(list)

# ==============================================
# MIDDLEWARE 1: Request Context Propagator
# ==============================================
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """
    Handles X-Request-ID header:
    - Reuses existing ID if provided
    - Generates new UUID4 if not provided
    - Always returns ID in response header
    """
    # Get or generate request ID
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid4())
    
    # Store in request state for later use
    request.state.request_id = request_id
    
    # Process the request
    response = await call_next(request)
    
    # Always include X-Request-ID in response headers
    response.headers["X-Request-ID"] = request_id
    
    return response

# ==============================================
# MIDDLEWARE 2: Per-Client Rate Limiter
# ==============================================
@app.middleware("http")
async def rate_limiter_middleware(request: Request, call_next):
    """
    Implements per-client rate limiting:
    - Uses X-Client-Id header for client identification
    - Allows 13 requests per 10 second window
    - Returns 429 when limit is exceeded
    - Different client IDs have independent buckets
    """
    # Skip rate limiting for preflight OPTIONS requests
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Identify client (default to "anonymous" if no header)
    client_id = request.headers.get("X-Client-Id", "anonymous")
    
    # Current timestamp
    now = time.time()
    
    # Clean up old timestamps (outside the window)
    client_requests[client_id] = [
        t for t in client_requests[client_id] 
        if now - t < WINDOW_SECONDS
    ]
    
    # Check if rate limit is exceeded
    if len(client_requests[client_id]) >= REQUEST_LIMIT:
        # Get or generate request ID for the 429 response
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid4())
        
        # Create 429 response
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"}
        )
        response.headers["X-Request-ID"] = request_id
        return response
    
    # Add current timestamp and proceed
    client_requests[client_id].append(now)
    return await call_next(request)

# ==============================================
# ENDPOINT: GET /ping
# ==============================================
@app.get("/ping")
async def ping_endpoint(request: Request):
    """
    Returns email and request_id in JSON response.
    The request_id comes from the context middleware.
    """
    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }

# ==============================================
# HEALTH CHECK (Optional - for debugging)
# ==============================================
@app.get("/")
async def root():
    """
    Root endpoint for health checks.
    Not required for the assignment but helpful for debugging.
    """
    return {"status": "healthy", "service": "FastAPI Middleware Demo"}

# ==============================================
# RUN CONFIGURATION (for local development)
# ==============================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
