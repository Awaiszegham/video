import os
import logging
from typing import Dict, Any, Optional
from celery import current_task
from celery_app import celery_app
from services.ai_services import (
    SpeechToTextService,
    TranslationService, 
    TextToSpeechService,
    AIWorkflowService
)
from services.storage_service import StorageManager

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def transcribe_audio_task(self, audio_path: str, language: Optional[str] = None, model_name: str = "base"):
    """Celery task for audio transcription"""
    try:
        task_id = self.request.id
        logger.info(f"Starting transcription task {task_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': 'Transcribing audio to text'}
        )
        
        # Initialize services
        stt_service = SpeechToTextService()
        storage_manager = StorageManager()
        
        # Transcribe audio
        result = await stt_service.transcribe_audio(audio_path, language, model_name)
        
        if 'error' not in result:
            # Save transcription as text file
            transcript_path = f"./processed/{task_id}_transcript.txt"
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(result['text'])
                f.write('\n\n--- Segments ---\n')
                for segment in result.get('segments', []):
                    f.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s]: {segment['text']}\n")
            
            # Upload transcript to storage
            remote_key = f"transcripts/{task_id}_transcript.txt"
            upload_result = await storage_manager.upload_file(
                transcript_path,
                remote_key,
                metadata={
                    'task_id': task_id,
                    'language': result.get('language', 'unknown'),
                    'model': model_name,
                    'original_file': os.path.basename(audio_path)
                }
            )
            
            if upload_result.get('success'):
                result['transcript_url'] = upload_result.get('url')
                result['remote_key'] = remote_key
                
                # Generate download URL
                download_result = await storage_manager.generate_signed_url(remote_key, 86400)
                if download_result.get('success'):
                    result['download_url'] = download_result['signed_url']
            
            result['task_id'] = task_id
            result['status'] = 'completed'
        
        return result
        
    except Exception as e:
        logger.error(f"Transcription task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def translate_text_task(self, text: str, target_language: str, source_language: Optional[str] = None):
    """Celery task for text translation"""
    try:
        task_id = self.request.id
        logger.info(f"Starting translation task {task_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': f'Translating to {target_language}'}
        )
        
        # Initialize services
        translation_service = TranslationService()
        storage_manager = StorageManager()
        
        # Translate text
        result = await translation_service.translate_text(text, target_language, source_language)
        
        if 'error' not in result:
            # Save translation as text file
            translation_path = f"./processed/{task_id}_translation.txt"
            with open(translation_path, 'w', encoding='utf-8') as f:
                f.write(f"Original ({result.get('source_language', 'unknown')}):\n")
                f.write(result['original_text'])
                f.write(f"\n\nTranslated ({target_language}):\n")
                f.write(result['translated_text'])
            
            # Upload translation to storage
            remote_key = f"translations/{task_id}_translation.txt"
            upload_result = await storage_manager.upload_file(
                translation_path,
                remote_key,
                metadata={
                    'task_id': task_id,
                    'source_language': result.get('source_language'),
                    'target_language': target_language
                }
            )
            
            if upload_result.get('success'):
                result['translation_url'] = upload_result.get('url')
                result['remote_key'] = remote_key
                
                # Generate download URL
                download_result = await storage_manager.generate_signed_url(remote_key, 86400)
                if download_result.get('success'):
                    result['download_url'] = download_result['signed_url']
            
            result['task_id'] = task_id
            result['status'] = 'completed'
        
        return result
        
    except Exception as e:
        logger.error(f"Translation task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def text_to_speech_task(
    self, 
    text: str, 
    language: str = "en", 
    voice: Optional[str] = None,
    provider: str = "google"
):
    """Celery task for text-to-speech conversion"""
    try:
        task_id = self.request.id
        logger.info(f"Starting TTS task {task_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': 'Converting text to speech'}
        )
        
        # Initialize services
        tts_service = TextToSpeechService()
        storage_manager = StorageManager()
        
        # Generate speech
        output_path = f"./processed/{task_id}_speech.mp3"
        result = await tts_service.synthesize_speech(text, language, voice, provider, output_path)
        
        if 'error' not in result:
            # Upload audio to storage
            remote_key = f"speech/{task_id}_speech.mp3"
            upload_result = await storage_manager.upload_file(
                result['audio_path'],
                remote_key,
                metadata={
                    'task_id': task_id,
                    'language': language,
                    'voice': voice or 'default',
                    'provider': provider,
                    'text_length': str(len(text))
                }
            )
            
            if upload_result.get('success'):
                result['speech_url'] = upload_result.get('url')
                result['remote_key'] = remote_key
                
                # Generate download URL
                download_result = await storage_manager.generate_signed_url(remote_key, 86400)
                if download_result.get('success'):
                    result['download_url'] = download_result['signed_url']
            
            result['task_id'] = task_id
            result['status'] = 'completed'
        
        return result
        
    except Exception as e:
        logger.error(f"TTS task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def ai_workflow_task(self, audio_path: str, target_language: str = "hi"):
    """Celery task for complete AI workflow"""
    try:
        task_id = self.request.id
        logger.info(f"Starting AI workflow task {task_id}")
        
        # Initialize services
        ai_workflow_service = AIWorkflowService()
        storage_manager = StorageManager()
        
        # Step 1: Transcribe
        self.update_state(
            state='PROGRESS',
            meta={'current': 1, 'total': 4, 'status': 'Transcribing audio'}
        )
        
        # Step 2: Translate
        self.update_state(
            state='PROGRESS',
            meta={'current': 2, 'total': 4, 'status': 'Translating text'}
        )
        
        # Step 3: Synthesize
        self.update_state(
            state='PROGRESS',
            meta={'current': 3, 'total': 4, 'status': 'Generating speech'}
        )
        
        # Execute workflow
        result = await ai_workflow_service.process_audio_workflow(audio_path, target_language, task_id)
        
        if result.get('status') == 'completed':
            # Step 4: Upload results
            self.update_state(
                state='PROGRESS',
                meta={'current': 4, 'total': 4, 'status': 'Uploading results'}
            )
            
            # Upload final audio to storage
            output_audio = result['output_audio']
            remote_key = f"workflows/{task_id}_translated_audio.mp3"
            
            upload_result = await storage_manager.upload_file(
                output_audio,
                remote_key,
                metadata={
                    'task_id': task_id,
                    'workflow_type': 'ai_complete',
                    'source_language': result.get('source_language'),
                    'target_language': target_language,
                    'original_file': os.path.basename(audio_path)
                }
            )
            
            if upload_result.get('success'):
                result['final_audio_url'] = upload_result.get('url')
                result['remote_key'] = remote_key
                
                # Generate download URL
                download_result = await storage_manager.generate_signed_url(remote_key, 86400)
                if download_result.get('success'):
                    result['download_url'] = download_result['signed_url']
        
        return result
        
    except Exception as e:
        logger.error(f"AI workflow task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

