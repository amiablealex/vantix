#!/usr/bin/env python3
"""
Generate secure random secrets for Vantix
Run this to create SECRET_KEY and REFRESH_TOKEN
"""

import secrets
import string

def generate_secret(length=64):
    """Generate a secure random secret"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_simple_token(length=32):
    """Generate a simpler token (alphanumeric only)"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

print("=" * 70)
print("Vantix Secret Generator")
print("=" * 70)
print()
print("Add these to your .env file:")
print()
print(f"SECRET_KEY={generate_secret(64)}")
print()
print(f"REFRESH_TOKEN={generate_simple_token(32)}")
print()
print("=" * 70)
