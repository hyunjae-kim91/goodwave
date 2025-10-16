import boto3
import os
import uuid
from io import BytesIO
from PIL import Image
import requests
from typing import Optional

from app.core.config import settings

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region
        )
        self.bucket_name = settings.s3_bucket

    async def upload_image_from_url(self, image_url: str, folder: str = "goodwave") -> Optional[str]:
        try:
            # Download image from URL
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Create unique filename
            file_extension = image_url.split('.')[-1].split('?')[0]
            if file_extension not in ['jpg', 'jpeg', 'png', 'gif']:
                file_extension = 'jpg'
            
            filename = f"{uuid.uuid4().hex}.{file_extension}"
            s3_key = f"{folder}/{filename}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=response.content,
                ContentType=f'image/{file_extension}',
                ACL='public-read'
            )
            
            # Return public URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
            return s3_url
            
        except Exception as e:
            print(f"Error uploading image to S3: {str(e)}")
            return None

    async def upload_instagram_thumbnail(self, image_url: str, username: str, post_type: str = "post") -> Optional[str]:
        folder = f"goodwave/instagram/{post_type}/{username}"
        return await self.upload_image_from_url(image_url, folder)

    async def delete_image(self, s3_url: str) -> bool:
        try:
            # Extract S3 key from URL
            s3_key = s3_url.split('.amazonaws.com/')[-1]
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
            
        except Exception as e:
            print(f"Error deleting image from S3: {str(e)}")
            return False

s3_service = S3Service()