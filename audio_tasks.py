import os
import logging
from typing import Dict, Any, List
from celery import current_task
from celery_app import celery_app
from services.audio_processor import AudioProcessor
from services.storage_service import StorageManager

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def process_audio_task(self, input_path: str, operations: List[str], parameters: Dict[str, Any] = None):
    """Celery task for audio processing"""
    try:
        task_id = self.request.id
        logger.info(f"Starting audio processing task {task_id}")
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': len(operations), 'status': 'Starting audio processing'}
        )
        
        # Initialize services
        audio_processor = AudioProcessor()
        storage_manager = StorageManager()
        
        # Process audio
        result = await audio_processor.process_audio(input_path, task_id, operations, parameters)
        
        if result.get('status') == 'completed':
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'current': len(operations), 'total': len(operations), 'status': 'Uploading to storage'}
            )
            
            # Upload result to storage
            output_path = result['output_path']
            remote_key = f"processed/audio/{task_id}_{os.path.basename(output_path)}"
            
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
        logger.error(f"Audio processing task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def noise_reduction_task(self, audio_path: str, noise_factor: float = 0.21):
    """Celery task for audio noise reduction"""
    try:
        task_id = self.request.id
        logger.info(f"Starting noise reduction task {task_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': 'Applying noise reduction'}
        )
        
        audio_processor = AudioProcessor()
        storage_manager = StorageManager()
        
        # Apply noise reduction
        result = await audio_processor.process_audio(
            audio_path, 
            task_id, 
            ['noise_reduction'],
            {'noise_factor': noise_factor}
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
        logger.error(f"Noise reduction task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def normalize_audio_task(self, audio_path: str, target_level: float = -3.0):
    """Celery task for audio normalization"""
    try:
        task_id = self.request.id
        logger.info(f"Starting audio normalization task {task_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': 'Normalizing audio levels'}
        )
        
        audio_processor = AudioProcessor()
        storage_manager = StorageManager()
        
        # Normalize audio
        result = await audio_processor.process_audio(
            audio_path,
            task_id,
            ['normalize_audio'],
            {'target_level': target_level}
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
        logger.error(f"Audio normalization task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def change_audio_speed_task(self, audio_path: str, speed_factor: float = 1.0, preserve_pitch: bool = True):
    """Celery task for changing audio speed"""
    try:
        task_id = self.request.id
        logger.info(f"Starting audio speed change task {task_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': f'Changing speed by factor {speed_factor}'}
        )
        
        audio_processor = AudioProcessor()
        storage_manager = StorageManager()
        
        # Change speed
        result = await audio_processor.process_audio(
            audio_path,
            task_id,
            ['change_speed'],
            {
                'speed_factor': speed_factor,
                'preserve_pitch': preserve_pitch
            }
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
        logger.error(f"Audio speed change task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

