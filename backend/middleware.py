# middleware.py

from flask import request, jsonify
import redis
import jwt
from datetime import datetime
from config.settings import JWT_SECRET, JWT_ALGORITHM
from utils.helpers import client

# Redis setup
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Rate limit settings
RATE_LIMIT = 5
EXPIRY_SECONDS = 24 * 60 * 60  # 24 hours

def decode_jwt(token):
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded
    except jwt.ExpiredSignatureError:
        return {'error': 'Token has expired'}
    except jwt.InvalidTokenError:
        return {'error': 'Invalid token'}

def is_rate_limited(user_id):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    redis_key = f"rate_limit:{user_id}:{today}"

    current_count = r.incr(redis_key)
    if current_count == 1:
        r.expire(redis_key, EXPIRY_SECONDS)

    if current_count > RATE_LIMIT:
        return True, current_count
    return False, current_count

def rate_limit_middleware(f):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401

        token = auth_header.split(' ')[1]
        decoded = decode_jwt(token)

        if 'error' in decoded:
            return jsonify(decoded), 401

        user_id = decoded.get('id') or decoded.get('email') or decoded.get('username') or 'anonymous'

        # Check rate limit
        limited, count = is_rate_limited(user_id)
        if limited:
            return jsonify({
                'error': 'Rate limit exceeded. Try again tomorrow.',
                'requests_today': count
            }), 429

        # Store the user info in Redis (optional)
        user_info_key = f"user:{user_id}"
        r.hset(user_info_key, mapping={
            'id': user_id,
            'last_active': datetime.utcnow().isoformat()
        })

        # Attach user info to request context
        request.user_info = decoded

        return f(*args, **kwargs)

    return wrapper
