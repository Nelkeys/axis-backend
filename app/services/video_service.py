import time
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from app.config import settings

# Configure Cloudinary once on import
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)


def upload_video_to_cloudinary(file) -> dict:
    """Upload a video, stored as 'authenticated' so it's never publicly accessible."""
    result = cloudinary.uploader.upload(
        file,
        resource_type="video",
        folder="axis-courses",
        type="authenticated",   # blocks direct public access
    )
    return result


def generate_signed_video_url(public_id: str, expires_in_seconds: int = 3600) -> str:
    """Generate a short-lived signed URL for playback."""
    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        resource_type="video",
        type="authenticated",
        sign_url=True,
        secure=True,
        expires_at=int(time.time()) + expires_in_seconds,
    )
    return url