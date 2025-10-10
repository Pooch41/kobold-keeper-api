import random
import string

from api.models import RecoveryKey


RANDOM_KEY_LENGTH = 10

def generate_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=RANDOM_KEY_LENGTH))