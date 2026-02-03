"""
Storage abstraction layer - supports local file system and Cloudflare R2.

For production: use Cloudflare R2 (S3-compatible)
For local dev: use /tmp/video-analyzer
"""

import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional
import uuid
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Storage configuration from environment
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "video-analyzer-videos")

# R2 Buckets for different access levels
R2_BENCHMARKS_BUCKET = os.getenv("R2_BENCHMARKS_BUCKET", "video-analyzer-benchmarks")
R2_USER_VIDEOS_BUCKET = os.getenv("R2_USER_VIDEOS_BUCKET", "video-analyzer-user-videos")

# Local storage path
LOCAL_STORAGE_PATH = "/tmp/video-analyzer"


class StorageAdapter:
    """Abstract storage adapter supporting local and R2."""

    def __init__(self):
        logger.info(f"Storage initialization:")
        logger.info(f"   R2_ENDPOINT_URL: {R2_ENDPOINT_URL[:30] + '...' if R2_ENDPOINT_URL else 'NOT SET'}")
        logger.info(f"   R2_ACCESS_KEY_ID: {'***' + R2_ACCESS_KEY_ID[-4:] if R2_ACCESS_KEY_ID else 'NOT SET'}")

        # Auto-detect: use R2 if credentials are available, otherwise local
        if all([R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]):
            self.storage_type = "r2"
            self.s3_client = boto3.client(
                's3',
                endpoint_url=R2_ENDPOINT_URL,
                aws_access_key_id=R2_ACCESS_KEY_ID,
                aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                region_name='auto'
            )
            self.bucket_name = R2_BUCKET_NAME
            logger.info(f"Cloudflare R2 storage initialized (auto-detected)")
            logger.info(f"   Buckets: {R2_BENCHMARKS_BUCKET} (public), {R2_USER_VIDEOS_BUCKET} (private)")
        else:
            self.storage_type = "local"
            os.makedirs(LOCAL_STORAGE_PATH, exist_ok=True)
            logger.warning(f"R2 credentials not found. Using local storage: {LOCAL_STORAGE_PATH}")

    def upload_video(self, file_content: bytes, filename: str) -> str:
        """Upload video to storage."""
        file_ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        if self.storage_type == "r2":
            return self._upload_to_r2(file_content, unique_filename)
        else:
            return self._upload_to_local(file_content, unique_filename)

    def _upload_to_r2(self, file_content: bytes, filename: str) -> str:
        """Upload to Cloudflare R2."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f"videos/{filename}",
                Body=file_content,
                ContentType="video/mp4"
            )
            public_url = f"{R2_ENDPOINT_URL}/{self.bucket_name}/videos/{filename}"
            logger.info(f"Video uploaded to R2: {filename}")
            return public_url
        except ClientError as e:
            logger.error(f"R2 upload failed: {e}")
            logger.warning("Falling back to local storage")
            return self._upload_to_local(file_content, filename)

    def _upload_to_local(self, file_content: bytes, filename: str) -> str:
        """Upload to local filesystem."""
        file_path = os.path.join(LOCAL_STORAGE_PATH, filename)
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_content)
        logger.info(f"Video saved locally: {filename}")
        return file_path

    def upload_benchmark(self, file_content: bytes, filename: str, metadata: dict = None) -> str:
        """Upload benchmark video to PUBLIC bucket."""
        file_ext = os.path.splitext(filename)[1]
        unique_filename = f"benchmark_{uuid.uuid4()}{file_ext}"

        if self.storage_type == "r2":
            return self._upload_benchmark_to_r2(file_content, unique_filename, metadata)
        else:
            return self._upload_to_local(file_content, unique_filename)

    def _upload_benchmark_to_r2(self, file_content: bytes, filename: str, metadata: dict = None) -> str:
        """Upload benchmark to R2 benchmark bucket (PUBLIC)."""
        try:
            extra_args = {
                "ContentType": "video/mp4",
                "ACL": "public-read",
            }
            if metadata:
                extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}

            self.s3_client.put_object(
                Bucket=R2_BENCHMARKS_BUCKET,
                Key=f"videos/{filename}",
                Body=file_content,
                **extra_args
            )
            public_url = f"{R2_ENDPOINT_URL}/{R2_BENCHMARKS_BUCKET}/videos/{filename}"
            logger.info(f"Benchmark uploaded to PUBLIC R2: {filename}")
            return public_url
        except ClientError as e:
            logger.error(f"R2 benchmark upload failed: {e}")
            return self._upload_to_local(file_content, filename)

    def upload_user_video(self, file_content: bytes, filename: str, user_id: str) -> str:
        """Upload user video to PRIVATE bucket."""
        file_ext = os.path.splitext(filename)[1]
        unique_filename = f"user_{user_id}/{uuid.uuid4()}{file_ext}"

        if self.storage_type == "r2":
            return self._upload_user_to_r2(file_content, unique_filename)
        else:
            return self._upload_to_local(file_content, unique_filename)

    def _upload_user_to_r2(self, file_content: bytes, filename: str) -> str:
        """Upload user video to R2 user-videos bucket (PRIVATE)."""
        try:
            logger.info(f"Uploading to R2: bucket={R2_USER_VIDEOS_BUCKET}, key=videos/{filename}")
            self.s3_client.put_object(
                Bucket=R2_USER_VIDEOS_BUCKET,
                Key=f"videos/{filename}",
                Body=file_content,
                ContentType="video/mp4"
            )
            internal_key = f"r2://{R2_USER_VIDEOS_BUCKET}/videos/{filename}"
            logger.info(f"User video uploaded to PRIVATE R2: {internal_key}")
            return internal_key
        except ClientError as e:
            logger.error(f"R2 user upload failed: {e}")
            return self._upload_to_local(file_content, filename)

    def generate_access_url(self, internal_key: str, expiration: int = 3600) -> str:
        """Generate temporary presigned URL for video access."""
        if not internal_key.startswith("r2://"):
            return internal_key

        parts = internal_key.replace("r2://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]

        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL (expires in {expiration}s)")
            return presigned_url
        except ClientError as e:
            logger.error(f"Presigned URL generation failed: {e}")
            return internal_key

    def get_upload_url(self, user_id: str, filename: str, expiration: int = 3600) -> dict:
        """Generate presigned PUT URL for direct client video upload."""
        if self.storage_type != "r2":
            raise ValueError("Presigned upload URLs only available for R2 storage")

        file_ext = os.path.splitext(filename)[1] or ".mp4"
        unique_filename = f"user_{user_id}/{uuid.uuid4()}{file_ext}"
        file_key = f"videos/{unique_filename}"

        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': R2_USER_VIDEOS_BUCKET,
                    'Key': file_key,
                    'ContentType': 'video/mp4'
                },
                ExpiresIn=expiration
            )
            internal_key = f"r2://{R2_USER_VIDEOS_BUCKET}/{file_key}"
            logger.info(f"Generated presigned PUT URL: {file_key}")
            return {
                "upload_url": presigned_url,
                "file_key": file_key,
                "internal_key": internal_key,
                "expires_in": expiration,
                "bucket": R2_USER_VIDEOS_BUCKET
            }
        except ClientError as e:
            logger.error(f"Presigned PUT URL generation failed: {e}")
            raise

    def get_file_content(self, internal_key: str) -> Optional[bytes]:
        """Download file content from R2 storage."""
        if not internal_key.startswith('r2://'):
            # Local file
            if os.path.exists(internal_key):
                with open(internal_key, 'rb') as f:
                    return f.read()
            logger.error(f"Local file not found: {internal_key}")
            return None

        try:
            parts = internal_key.replace('r2://', '').split('/', 1)
            if len(parts) != 2:
                logger.error(f"Invalid R2 path format: {internal_key}")
                return None

            bucket_name, object_key = parts
            response = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
            content = response['Body'].read()
            logger.info(f"Downloaded {len(content)} bytes from R2: {internal_key}")
            return content
        except Exception as e:
            logger.error(f"Failed to download from R2: {e}")
            return None

    def delete_video(self, path_or_url: str) -> bool:
        """Delete video from storage."""
        if self.storage_type == "r2" and path_or_url.startswith("r2://"):
            parts = path_or_url.replace("r2://", "").split("/", 1)
            bucket = parts[0]
            key = parts[1]
            try:
                self.s3_client.delete_object(Bucket=bucket, Key=key)
                logger.info(f"Deleted from R2: {key}")
                return True
            except ClientError as e:
                logger.error(f"R2 delete failed: {e}")
                return False
        else:
            if os.path.exists(path_or_url):
                os.remove(path_or_url)
                logger.info(f"Deleted local file: {path_or_url}")
                return True
            return False


# Singleton instance
_storage_adapter: Optional[StorageAdapter] = None


def get_storage() -> StorageAdapter:
    """Get storage adapter singleton."""
    global _storage_adapter
    if _storage_adapter is None:
        _storage_adapter = StorageAdapter()
    return _storage_adapter
