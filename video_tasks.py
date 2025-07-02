import os
import logging
from typing import Dict, Any, List
from celery import current_task
from celery_app import celery_app
from services.video_processor import VideoProcessor
from services.storage_service import StorageManager

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def process_video_task(self, input_path: str, operations: List[str], parameters: Dict[str, Any] = None):
    """Celery task for video processing"""
    try:
        task_id = self.request.id
        logger.info(f"Starting video processing task {task_id}")
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': len(operations), 'status': 'Starting video processing'}
        )
        
        # Initialize services
        video_processor = VideoProcessor()
        storage_manager = StorageManager()
        
        # Process video
        result = await video_processor.process_video(input_path, task_id, operations, parameters)
        
        if result.get('status') == 'completed':
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'current': len(operations), 'total': len(operations), 'status': 'Uploading to storage'}
            )
            
            # Upload result to storage
            output_path = result['output_path']
            remote_key = f"processed/video/{task_id}_{os.path.basename(output_path)}"
            
            upload_result = await storage_manager.upload_file(
                output_path, 
                remote_key,
                metadata={
                    'task_id': task_id,
                    'operations': ','.join(operations),
                    'original_file': os.path.basename(input_path)
                }
            )
            
            if upload_result.get('success'):
                result['storage_url'] = upload_result.get('url')
                result['remote_key'] = remote_key
            
            # Generate signed download URL
            download_result = await storage_manager.generate_signed_url(remote_key, 86400)  # 24 hours
            if download_result.get('success'):
                result['download_url'] = download_result['signed_url']
        
        return result
        
    except Exception as e:
        logger.error(f"Video processing task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def extract_audio_task(self, video_path: str, audio_format: str = 'mp3'):
    """Celery task for audio extraction from video"""
    try:
        task_id = self.request.id
        logger.info(f"Starting audio extraction task {task_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': 'Extracting audio from video'}
        )
        
        video_processor = VideoProcessor()
        storage_manager = StorageManager()
        
        # Extract audio
        result = await video_processor.process_video(
            video_path, 
            task_id, 
            ['extract_audio'],
            {'audio_format': audio_format}
        )
        
        if result.get('status') == 'completed':
            # Upload to storage
            output_path = result['output_path']
            remote_key = f"processed/audio/{task_id}_{os.path.basename(output_path)}"
            
            upload_result = await storage_manager.upload_file(output_path, remote_key)
            
            if upload_result.get('success'):
                result['storage_url'] = upload_result.get('url')
                result['remote_key'] = remote_key
                
                # Generate download URL
                download_result = await storage_manager.generate_signed_url(remote_key, 86400)
                if download_result.get('success'):
                    result['download_url'] = download_result['signed_url']
        
        return result
        
    except Exception as e:
        logger.error(f"Audio extraction task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def convert_video_format_task(self, input_path: str, target_format: str, video_codec: str = 'libx264'):
    """Celery task for video format conversion"""
    try:
        task_id = self.request.id
        logger.info(f"Starting video format conversion task {task_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': f'Converting to {target_format}'}
        )
        
        video_processor = VideoProcessor()
        storage_manager = StorageManager()
        
        # Convert format
        result = await video_processor.process_video(
            input_path,
            task_id,
            ['convert_format'],
            {
                'target_format': target_format,
                'video_codec': video_codec
            }
        )
        
        if result.get('status') == 'completed':
            # Upload to storage
            output_path = result['output_path']
            remote_key = f"processed/video/{task_id}_{os.path.basename(output_path)}"
            
            upload_result = await storage_manager.upload_file(output_path, remote_key)
            
            if upload_result.get('success'):
                result['storage_url'] = upload_result.get('url')
                result['remote_key'] = remote_key
                
                # Generate download URL
                download_result = await storage_manager.generate_signed_url(remote_key, 86400)
                if download_result.get('success'):
                    result['download_url'] = download_result['signed_url']
        
        return result
        
    except Exception as e:
        logger.error(f"Video format conversion task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

