"""
Rate limiter configuration
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])