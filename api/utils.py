import random
import string

from api.models import RecoveryKey


RANDOM_KEY_LENGTH = 10

def generate_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=RANDOM_KEY_LENGTH))

def generate_unique_key():
    data = RecoveryKey.objects
    key = generate_key()

    while True:
        key_exists = data.filter(recovery_key=key).exists()
        if key_exists:
            key = generate_key()
        else:
            break

    return key