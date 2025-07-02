import os
import logging
import tempfile
from typing import Dict, Any, Optional, List
import whisper
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech
import boto3
from pathlib import Path

logger = logging.getLogger(__name__)

class SpeechToTextService:
    """Service for speech-to-text using OpenAI Whisper"""
    
    def __init__(self):
        self.model = None
        self.model_name = "base"  # Default model
    
    def load_model(self, model_name: str = "base"):
        """Load Whisper model"""
        try:
            if self.model is None or self.model_name != model_name:
                logger.info(f"Loading Whisper model: {model_name}")
                self.model = whisper.load_model(model_name)
                self.model_name = model_name
            return True
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {str(e)}")
            return False
    
    async def transcribe_audio(
        self, 
        audio_path: str, 
        language: Optional[str] = None,
        model_name: str = "base"
    ) -> Dict[str, Any]:
        """Transcribe audio file to text"""
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            # Load model if needed
            if not self.load_model(model_name):
                raise Exception("Failed to load Whisper model")
            
            logger.info(f"Transcribing audio: {audio_path}")
            
            # Transcribe with Whisper
            options = {}
            if language and language != "auto":
                options["language"] = language
            
            result = self.model.transcribe(audio_path, **options)
            
            # Extract segments with timestamps
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip()
                })
            
            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": segments,
                "duration": segments[-1]["end"] if segments else 0
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            return {"error": str(e)}
    
    def get_available_models(self) -> List[str]:
        """Get list of available Whisper models"""
        return ["tiny", "base", "small", "medium", "large"]

class TranslationService:
    """Service for text translation using Google Translate"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Translate client"""
        try:
            # Check if credentials are available
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                self.client = translate.Client()
                logger.info("Google Translate client initialized")
            else:
                logger.warning("Google Translate credentials not found")
        except Exception as e:
            logger.error(f"Failed to initialize Google Translate client: {str(e)}")
    
    async def translate_text(
        self, 
        text: str, 
        target_language: str,
        source_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Translate text to target language"""
        try:
            if not self.client:
                return {"error": "Google Translate client not available"}
            
            logger.info(f"Translating text to {target_language}")
            
            # Perform translation
            result = self.client.translate(
                text,
                target_language=target_language,
                source_language=source_language
            )
            
            return {
                "translated_text": result["translatedText"],
                "source_language": result.get("detectedSourceLanguage", source_language),
                "target_language": target_language,
                "original_text": text
            }
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return {"error": str(e)}
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages"""
        try:
            if not self.client:
                return []
            
            languages = self.client.get_languages()
            return [{"code": lang["language"], "name": lang["name"]} for lang in languages]
            
        except Exception as e:
            logger.error(f"Failed to get supported languages: {str(e)}")
            return []

class TextToSpeechService:
    """Service for text-to-speech using Google TTS and AWS Polly"""
    
    def __init__(self):
        self.google_client = None
        self.aws_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize TTS clients"""
        try:
            # Initialize Google TTS
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                self.google_client = texttospeech.TextToSpeechClient()
                logger.info("Google TTS client initialized")
            
            # Initialize AWS Polly
            aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
            aws_region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
            
            if aws_access_key and aws_secret_key:
                self.aws_client = boto3.client(
                    'polly',
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    region_name=aws_region
                )
                logger.info("AWS Polly client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS clients: {str(e)}")
    
    async def synthesize_speech(
        self, 
        text: str, 
        language: str = "en",
        voice: Optional[str] = None,
        provider: str = "google",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert text to speech"""
        try:
            if provider == "google" and self.google_client:
                return await self._google_tts(text, language, voice, output_path)
            elif provider == "aws" and self.aws_client:
                return await self._aws_polly_tts(text, language, voice, output_path)
            else:
                return {"error": f"TTS provider '{provider}' not available"}
                
        except Exception as e:
            logger.error(f"Speech synthesis failed: {str(e)}")
            return {"error": str(e)}
    
    async def _google_tts(
        self, 
        text: str, 
        language: str,
        voice: Optional[str],
        output_path: Optional[str]
    ) -> Dict[str, Any]:
        """Google TTS implementation"""
        try:
            # Set up the text input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Configure voice
            voice_config = texttospeech.VoiceSelectionParams(
                language_code=language,
                name=voice if voice else None
            )
            
            # Configure audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            # Perform synthesis
            response = self.google_client.synthesize_speech(
                input=synthesis_input,
                voice=voice_config,
                audio_config=audio_config
            )
            
            # Save audio file
            if not output_path:
                output_path = tempfile.mktemp(suffix=".mp3")
            
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
            
            return {
                "audio_path": output_path,
                "provider": "google",
                "language": language,
                "voice": voice,
                "text": text
            }
            
        except Exception as e:
            logger.error(f"Google TTS failed: {str(e)}")
            raise
    
    async def _aws_polly_tts(
        self, 
        text: str, 
        language: str,
        voice: Optional[str],
        output_path: Optional[str]
    ) -> Dict[str, Any]:
        """AWS Polly TTS implementation"""
        try:
            # Map language codes to Polly voices
            polly_voices = {
                "en": voice or "Joanna",
                "hi": voice or "Aditi",  # Hindi voice
                "es": voice or "Penelope",
                "fr": voice or "Celine",
                "de": voice or "Marlene"
            }
            
            voice_id = polly_voices.get(language, "Joanna")
            
            # Synthesize speech
            response = self.aws_client.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=voice_id
            )
            
            # Save audio file
            if not output_path:
                output_path = tempfile.mktemp(suffix=".mp3")
            
            with open(output_path, "wb") as out:
                out.write(response['AudioStream'].read())
            
            return {
                "audio_path": output_path,
                "provider": "aws",
                "language": language,
                "voice": voice_id,
                "text": text
            }
            
        except Exception as e:
            logger.error(f"AWS Polly TTS failed: {str(e)}")
            raise
    
    def get_available_voices(self, provider: str = "google") -> List[Dict[str, Any]]:
        """Get available voices for TTS"""
        try:
            if provider == "google" and self.google_client:
                voices = self.google_client.list_voices()
                return [
                    {
                        "name": voice.name,
                        "language": voice.language_codes[0],
                        "gender": voice.ssml_gender.name
                    }
                    for voice in voices.voices
                ]
            elif provider == "aws" and self.aws_client:
                voices = self.aws_client.describe_voices()
                return [
                    {
                        "name": voice["Id"],
                        "language": voice["LanguageCode"],
                        "gender": voice["Gender"]
                    }
                    for voice in voices["Voices"]
                ]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get voices for {provider}: {str(e)}")
            return []

class AIWorkflowService:
    """Service for AI workflow automation"""
    
    def __init__(self):
        self.stt_service = SpeechToTextService()
        self.translation_service = TranslationService()
        self.tts_service = TextToSpeechService()
    
    async def process_audio_workflow(
        self,
        audio_path: str,
        target_language: str = "hi",  # Hindi
        task_id: str = None
    ) -> Dict[str, Any]:
        """Complete audio processing workflow: transcribe -> translate -> synthesize"""
        try:
            logger.info(f"Starting AI workflow for task {task_id}")
            
            # Step 1: Transcribe audio
            transcription = await self.stt_service.transcribe_audio(audio_path)
            if "error" in transcription:
                return {"error": f"Transcription failed: {transcription['error']}"}
            
            # Step 2: Translate text
            translation = await self.translation_service.translate_text(
                transcription["text"],
                target_language
            )
            if "error" in translation:
                return {"error": f"Translation failed: {translation['error']}"}
            
            # Step 3: Synthesize translated text
            output_path = f"./processed/{task_id}_translated_audio.mp3" if task_id else None
            synthesis = await self.tts_service.synthesize_speech(
                translation["translated_text"],
                target_language,
                output_path=output_path
            )
            if "error" in synthesis:
                return {"error": f"Speech synthesis failed: {synthesis['error']}"}
            
            return {
                "task_id": task_id,
                "status": "completed",
                "original_text": transcription["text"],
                "translated_text": translation["translated_text"],
                "source_language": transcription["language"],
                "target_language": target_language,
                "output_audio": synthesis["audio_path"],
                "segments": transcription.get("segments", [])
            }
            
        except Exception as e:
            logger.error(f"AI workflow failed: {str(e)}")
            return {"error": str(e)}

