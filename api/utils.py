"""
Utility functions for the API application.

This module provides common helpers, such as the cryptographic key generation
function used for features like password recovery.
"""

import random
import string

RANDOM_KEY_LENGTH = 10


def generate_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=RANDOM_KEY_LENGTH))
