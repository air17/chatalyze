from django.core.files.storage import FileSystemStorage

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

private_storage = FileSystemStorage(location="usersfiles")
