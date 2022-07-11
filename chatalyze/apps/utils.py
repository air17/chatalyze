import os
import uuid

from django.utils.deconstruct import deconstructible


@deconstructible
class RandomFileName:
    """Generates a file name for the Django model using uuid"""

    def __init__(self, path):
        self.path = os.path.join(path, "%s%s")

    def __call__(self, _, filename):
        extension = os.path.splitext(filename)[1]
        return self.path % (uuid.uuid4(), extension)
