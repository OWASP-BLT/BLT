from django.conf import settings
from storages.backends.gcloud import GoogleCloudStorage


class PrivateGoogleCloudStorage(GoogleCloudStorage):
    """Private GCS storage for hidden/private issue screenshots."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bucket_name", settings.GS_PRIVATE_BUCKET_NAME)
        super().__init__(*args, **kwargs)
