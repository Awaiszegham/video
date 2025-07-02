import os
import logging
from typing import Dict, Any, Optional
from celery import current_task
from celery_app import celery_app
from services.storage_service import StorageManager

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def upload_file_task(self, local_path: str, remote_key: str, metadata: Optional[Dict[str, str]] = None):
    """Celery task for file upload to storage"""
    try:
        task_id = self.request.id
        logger.info(f"Starting file upload task {task_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': f'Uploading {os.path.basename(local_path)}'}
        )
        
        # Initialize storage manager
        storage_manager = StorageManager()
        
        # Upload file
        result = await storage_manager.upload_file(local_path, remote_key, metadata)
        
        if result.get('success'):
            result['task_id'] = task_id
            result['status'] = 'completed'
            
            # Generate signed URL for immediate access
            download_result = await storage_manager.generate_signed_url(remote_key, 86400)
            if download_result.get('success'):
                result['download_url'] = download_result['signed_url']
        
        return result
        
    except Exception as e:
        logger.error(f"File upload task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def batch_upload_task(self, file_paths: list, remote_prefix: str = "batch"):
    """Celery task for batch file upload"""
    try:
        task_id = self.request.id
        logger.info(f"Starting batch upload task {task_id}")
        
        storage_manager = StorageManager()
        results = []
        total_files = len(file_paths)
        
        for i, file_path in enumerate(file_paths):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i,
                    'total': total_files,
                    'status': f'Uploading {os.path.basename(file_path)} ({i+1}/{total_files})'
                }
            )
            
            # Generate remote key
            filename = os.path.basename(file_path)
            remote_key = f"{remote_prefix}/{filename}"
            
            # Upload file
            upload_result = await storage_manager.upload_file(
                file_path,
                remote_key,
                metadata={
                    'batch_id': task_id,
                    'file_index': str(i),
                    'total_files': str(total_files)
                }
            )
            
            results.append({
                'file_path': file_path,
                'remote_key': remote_key,
                'result': upload_result
            })
        
        # Summary
        successful_uploads = sum(1 for r in results if r['result'].get('success'))
        
        return {
            'task_id': task_id,
            'status': 'completed',
            'total_files': total_files,
            'successful_uploads': successful_uploads,
            'failed_uploads': total_files - successful_uploads,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Batch upload task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def cleanup_old_files_task(self, max_age_days: int = 7):
    """Celery task for cleaning up old files"""
    try:
        task_id = self.request.id
        logger.info(f"Starting cleanup task {task_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': 'Scanning for old files'}
        )
        
        storage_manager = StorageManager()
        
        # List all files
        list_result = await storage_manager.list_files()
        
        if not list_result.get('success'):
            return {'error': 'Failed to list files'}
        
        files = list_result['files']
        deleted_files = []
        errors = []
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for i, file_info in enumerate(files):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i,
                    'total': len(files),
                    'status': f'Checking {file_info["key"]}'
                }
            )
            
            # Parse last modified date
            try:
                file_date = datetime.fromisoformat(file_info['last_modified'].replace('Z', '+00:00'))
                
                if file_date < cutoff_date:
                    # Delete old file
                    delete_result = await storage_manager.delete_file(file_info['key'])
                    
                    if delete_result.get('success'):
                        deleted_files.append(file_info['key'])
                    else:
                        errors.append({
                            'file': file_info['key'],
                            'error': delete_result.get('error', 'Unknown error')
                        })
                        
            except Exception as e:
                errors.append({
                    'file': file_info['key'],
                    'error': f'Date parsing error: {str(e)}'
                })
        
        return {
            'task_id': task_id,
            'status': 'completed',
            'max_age_days': max_age_days,
            'total_files_checked': len(files),
            'deleted_files': deleted_files,
            'deleted_count': len(deleted_files),
            'errors': errors,
            'error_count': len(errors)
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def generate_download_links_task(self, remote_keys: list, expiration: int = 3600):
    """Celery task for generating multiple download links"""
    try:
        task_id = self.request.id
        logger.info(f"Starting download links generation task {task_id}")
        
        storage_manager = StorageManager()
        results = []
        
        for i, remote_key in enumerate(remote_keys):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i,
                    'total': len(remote_keys),
                    'status': f'Generating link for {remote_key}'
                }
            )
            
            # Generate signed URL
            url_result = await storage_manager.generate_signed_url(remote_key, expiration)
            
            results.append({
                'remote_key': remote_key,
                'result': url_result
            })
        
        return {
            'task_id': task_id,
            'status': 'completed',
            'expiration': expiration,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Download links generation task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

