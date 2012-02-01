import hashlib
import os


class StorageBase(object):

    def new_token(self, bits=264):
        """Get a new random token with `bits` bits of randomness."""
        return hashlib.sha1(os.urandom(bits)).hexdigest()
