import jwt
from flask import request, g, jsonify
from functools import wraps
import redis
import uuid
import time

JWT_SECRET = 'JiGX5rgVfN6FiBOuCGjq+Q=='
JWT_ALGORITHM = 'HS256'



# Setup Redis client
r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

# Define rate limit parameters
MAX_REQUESTS_PER_DAY = 5  # Max 5 requests per day
TTL_SECONDS = 86400  # 24 hours (in seconds)

def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401

        token = auth_header.split(' ')[1]

        try:
            # Decode the JWT token and extract user information
            decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            print("Decoded JWT:", decoded)  # Debugging line to see the decoded token

            # Attach user details to the global g object
            g.user = decoded
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        # Proceed to the actual route function
        return f(*args, **kwargs)
    return decorated_function

def check_rate_limit(user_id: str):
    """Check if the user has exceeded the rate limit."""
    # Redis key for tracking requests per user
    redis_key = f"rate_limit:{user_id}"

    # Get the current request count and timestamp
    request_count = r.get(redis_key)

    # If no request count exists, create one and set expiration (TTL)
    if not request_count:
        r.setex(redis_key, TTL_SECONDS, 1)  # 1st request today
        return True

    # If request count exceeds the limit, deny access
    if int(request_count) >= MAX_REQUESTS_PER_DAY:
        return False

    # Otherwise, increment the request count
    r.incr(redis_key)
    return True
