from django.conf import settings
from .base import BaseStorageProvider


class S3StorageProvider(BaseStorageProvider):
    def __init__(self):
        try:
            import boto3
            self.s3 = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            self.bucket = settings.AWS_STORAGE_BUCKET_NAME
        except ImportError:
            raise ImportError('boto3 is required for S3 storage. Install it with: pip install boto3')

    def upload(self, file_obj, file_key, content_type=None, **kwargs):
        extra = {}
        if content_type:
            extra['ContentType'] = content_type
        self.s3.upload_fileobj(file_obj, self.bucket, file_key, ExtraArgs=extra)
        return file_key

    def delete(self, file_key, **kwargs):
        self.s3.delete_object(Bucket=self.bucket, Key=file_key)

    def generate_signed_url(self, file_key, expires_in=3600, **kwargs):
        return self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': file_key},
            ExpiresIn=expires_in
        )

    def get_url(self, file_key, **kwargs):
        return f"https://{self.bucket}.s3.amazonaws.com/{file_key}"

    def get_provider_name(self):
        return 's3'
