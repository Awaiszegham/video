import os
import logging
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
from pathlib import Path
import mimetypes
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CloudflareR2Service:
    """Service for Cloudflare R2 storage (S3-compatible)"""
    
    def __init__(self):
        self.client = None
        self.bucket_name = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Cloudflare R2 client"""
        try:
            # Get R2 credentials from environment
            account_id = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
            access_key = os.environ.get('CLOUDFLARE_R2_ACCESS_KEY_ID')
            secret_key = os.environ.get('CLOUDFLARE_R2_SECRET_ACCESS_KEY')
            self.bucket_name = os.environ.get('CLOUDFLARE_R2_BUCKET_NAME')
            
            if not all([account_id, access_key, secret_key, self.bucket_name]):
                logger.warning("Cloudflare R2 credentials not found, using local storage")
                return
            
            # Configure R2 endpoint
            endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
            
            # Create S3 client for R2
            self.client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(
                    region_name='auto',
                    retries={'max_attempts': 3}
                )
            )
            
            # Test connection
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info("Cloudflare R2 client initialized successfully")
            
        except NoCredentialsError:
            logger.warning("R2 credentials not found")
        except ClientError as e:
            logger.error(f"Failed to initialize R2 client: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error initializing R2: {str(e)}")
    
    async def upload_file(
        self, 
        local_path: str, 
        remote_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload file to R2 storage"""
        try:
            if not self.client:
                return {"error": "R2 client not available"}
            
            if not os.path.exists(local_path):
                return {"error": f"Local file not found: {local_path}"}
            
            logger.info(f"Uploading {local_path} to R2 as {remote_key}")
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(local_path)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Prepare upload parameters
            upload_params = {
                'Bucket': self.bucket_name,
                'Key': remote_key,
                'ContentType': content_type
            }
            
            # Add metadata if provided
            if metadata:
                upload_params['Metadata'] = metadata
            
            # Upload file
            with open(local_path, 'rb') as file:
                self.client.upload_fileobj(file, **upload_params)
            
            # Get file info
            file_size = os.path.getsize(local_path)
            
            return {
                "success": True,
                "remote_key": remote_key,
                "bucket": self.bucket_name,
                "size": file_size,
                "content_type": content_type,
                "url": f"https://{self.bucket_name}.r2.dev/{remote_key}"
            }
            
        except ClientError as e:
            logger.error(f"R2 upload failed: {str(e)}")
            return {"error": f"Upload failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected upload error: {str(e)}")
            return {"error": str(e)}
    
    async def generate_signed_url(
        self, 
        remote_key: str, 
        expiration: int = 3600
    ) -> Dict[str, Any]:
        """Generate signed URL for file download"""
        try:
            if not self.client:
                return {"error": "R2 client not available"}
            
            logger.info(f"Generating signed URL for {remote_key}")
            
            # Generate presigned URL
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': remote_key},
                ExpiresIn=expiration
            )
            
            return {
                "success": True,
                "signed_url": url,
                "expires_in": expiration,
                "expires_at": (datetime.now() + timedelta(seconds=expiration)).isoformat()
            }
            
        except ClientError as e:
            logger.error(f"Failed to generate signed URL: {str(e)}")
            return {"error": f"Signed URL generation failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error generating signed URL: {str(e)}")
            return {"error": str(e)}
    
    async def delete_file(self, remote_key: str) -> Dict[str, Any]:
        """Delete file from R2 storage"""
        try:
            if not self.client:
                return {"error": "R2 client not available"}
            
            logger.info(f"Deleting {remote_key} from R2")
            
            self.client.delete_object(Bucket=self.bucket_name, Key=remote_key)
            
            return {"success": True, "deleted_key": remote_key}
            
        except ClientError as e:
            logger.error(f"R2 delete failed: {str(e)}")
            return {"error": f"Delete failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected delete error: {str(e)}")
            return {"error": str(e)}
    
    async def list_files(self, prefix: str = "") -> Dict[str, Any]:
        """List files in R2 bucket"""
        try:
            if not self.client:
                return {"error": "R2 client not available"}
            
            logger.info(f"Listing files with prefix: {prefix}")
            
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "etag": obj['ETag'].strip('"')
                })
            
            return {
                "success": True,
                "files": files,
                "count": len(files)
            }
            
        except ClientError as e:
            logger.error(f"R2 list failed: {str(e)}")
            return {"error": f"List failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected list error: {str(e)}")
            return {"error": str(e)}
    
    def is_available(self) -> bool:
        """Check if R2 service is available"""
        return self.client is not None

class LocalStorageService:
    """Fallback local storage service"""
    
    def __init__(self, storage_dir: str = "./storage"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    async def upload_file(
        self, 
        local_path: str, 
        remote_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Copy file to local storage"""
        try:
            if not os.path.exists(local_path):
                return {"error": f"Local file not found: {local_path}"}
            
            # Create destination path
            dest_path = os.path.join(self.storage_dir, remote_key)
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            
            # Copy file
            import shutil
            shutil.copy2(local_path, dest_path)
            
            file_size = os.path.getsize(dest_path)
            
            return {
                "success": True,
                "remote_key": remote_key,
                "local_path": dest_path,
                "size": file_size,
                "url": f"/storage/{remote_key}"
            }
            
        except Exception as e:
            logger.error(f"Local storage upload failed: {str(e)}")
            return {"error": str(e)}
    
    async def generate_signed_url(
        self, 
        remote_key: str, 
        expiration: int = 3600
    ) -> Dict[str, Any]:
        """Generate local file URL"""
        try:
            file_path = os.path.join(self.storage_dir, remote_key)
            
            if not os.path.exists(file_path):
                return {"error": "File not found"}
            
            return {
                "success": True,
                "signed_url": f"/storage/{remote_key}",
                "expires_in": expiration,
                "local_path": file_path
            }
            
        except Exception as e:
            logger.error(f"Local URL generation failed: {str(e)}")
            return {"error": str(e)}
    
    async def delete_file(self, remote_key: str) -> Dict[str, Any]:
        """Delete file from local storage"""
        try:
            file_path = os.path.join(self.storage_dir, remote_key)
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return {"success": True, "deleted_key": remote_key}
            
        except Exception as e:
            logger.error(f"Local delete failed: {str(e)}")
            return {"error": str(e)}
    
    async def list_files(self, prefix: str = "") -> Dict[str, Any]:
        """List files in local storage"""
        try:
            files = []
            
            for root, dirs, filenames in os.walk(self.storage_dir):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, self.storage_dir)
                    
                    if relative_path.startswith(prefix):
                        stat = os.stat(file_path)
                        files.append({
                            "key": relative_path.replace(os.sep, '/'),
                            "size": stat.st_size,
                            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "local_path": file_path
                        })
            
            return {
                "success": True,
                "files": files,
                "count": len(files)
            }
            
        except Exception as e:
            logger.error(f"Local list failed: {str(e)}")
            return {"error": str(e)}

class StorageManager:
    """Unified storage manager that uses R2 or falls back to local storage"""
    
    def __init__(self):
        self.r2_service = CloudflareR2Service()
        self.local_service = LocalStorageService()
        
        # Use R2 if available, otherwise local storage
        self.primary_service = (
            self.r2_service if self.r2_service.is_available() 
            else self.local_service
        )
        
        logger.info(f"Using {'Cloudflare R2' if self.r2_service.is_available() else 'local'} storage")
    
    async def upload_file(
        self, 
        local_path: str, 
        remote_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload file using primary storage service"""
        return await self.primary_service.upload_file(local_path, remote_key, metadata)
    
    async def generate_signed_url(
        self, 
        remote_key: str, 
        expiration: int = 3600
    ) -> Dict[str, Any]:
        """Generate signed URL using primary storage service"""
        return await self.primary_service.generate_signed_url(remote_key, expiration)
    
    async def delete_file(self, remote_key: str) -> Dict[str, Any]:
        """Delete file using primary storage service"""
        return await self.primary_service.delete_file(remote_key)
    
    async def list_files(self, prefix: str = "") -> Dict[str, Any]:
        """List files using primary storage service"""
        return await self.primary_service.list_files(prefix)
    
    def get_storage_type(self) -> str:
        """Get the type of storage being used"""
        return "cloudflare_r2" if self.r2_service.is_available() else "local"

