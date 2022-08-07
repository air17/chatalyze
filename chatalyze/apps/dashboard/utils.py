from django.core.cache import cache


class ProgressBar:
    """Progress bar value stored in cache"""

    def __init__(self, progress_id: str, timeout: int = 60 * 60):
        self.progress_id = progress_id
        self._value = 0
        self.timeout = timeout

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val: int):
        if self._value != val:
            self._value = val
            cache.set(f"task-progress:{self.progress_id}", val, timeout=self.timeout)

    @value.deleter
    def value(self):
        self._value = None
        cache.delete(f"task-progress:{self.progress_id}")
