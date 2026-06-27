"""Input validation and output sanitization guardrails."""

import re
from typing import Tuple, Optional

# Maximum query length to prevent abuse
MAX_QUERY_LENGTH = 10000

# Patterns that should not appear in error messages
SENSITIVE_PATTERNS = [
    r'password\s*=\s*\S+',
    r'api[_-]?key\s*=\s*\S+',
    r'secret\s*=\s*\S+',
    r'token\s*=\s*\S+',
    r'\/home\/[^\/]+\/',
    r'\/users\/[^\/]+\/',
    r'C:\\Users\\[^\\]+\\',
    r'connection\s+string',
]


def validate_query_input(query: str) -> Tuple[bool, Optional[str]]:
    """
    Validate user query input.
    
    Args:
        query: The user's query string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "Query cannot be empty"
    
    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query is too long (maximum {MAX_QUERY_LENGTH} characters)"
    
    # Check for potential injection attempts
    dangerous_patterns = [
        r'<script[^>]*>',
        r'javascript:',
        r'on\w+\s*=',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return False, "Query contains potentially dangerous content"
    
    return True, None


def sanitize_error_message(error_message: str) -> str:
    """
    Sanitize error messages to prevent information leakage.
    
    Args:
        error_message: The original error message
        
    Returns:
        Sanitized error message with sensitive information removed
    """
    sanitized = error_message
    
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
    
    return sanitized
