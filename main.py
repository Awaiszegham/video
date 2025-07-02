from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import tempfile
import shutil
from pathlib import Path
import uuid
import logging

# Import processing modules
from services.video_processor import VideoProcessor
from services.audio_processor import AudioProcessor
from services.download_service import DownloadService
from services.ai_services import (
    SpeechToTextService, 
    TranslationService, 
    TextToSpeechService,
    AIWorkflowService
)
from services.storage_service import StorageManager
from models.schemas import (
    DownloadRequest, 
    ProcessingRequest, 
    ProcessingResponse,
    TaskStatus,
    TranscriptionRequest,
    TranslationRequest,
    TTSRequest,
    WorkflowRequest,
    WorkflowResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Audio/Video Processing API",
    description="Complete audio/video processing pipeline with AI services",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = os.environ.get('UPLOAD_DIR', './uploads')
PROCESSED_DIR = os.environ.get('PROCESSED_DIR', './processed')
DOWNLOAD_DIR = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', './videos')

# Ensure directories exist
for directory in [UPLOAD_DIR, PROCESSED_DIR, DOWNLOAD_DIR]:
    os.makedirs(directory, exist_ok=True)

# Initialize services
video_processor = VideoProcessor()
audio_processor = AudioProcessor()
download_service = DownloadService(DOWNLOAD_DIR)
stt_service = SpeechToTextService()
translation_service = TranslationService()
tts_service = TextToSpeechService()
ai_workflow_service = AIWorkflowService()
storage_manager = StorageManager()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Audio/Video Processing API is running", "status": "healthy"}

@app.post("/download", response_model=ProcessingResponse)
async def download_video(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Download video from URL (YouTube, etc.)"""
    try:
        task_id = str(uuid.uuid4())
        
        # Start background download task
        background_tasks.add_task(
            download_service.download_video,
            request.url,
            task_id,
            request.format_preference
        )
        
        return ProcessingResponse(
            task_id=task_id,
            status="started",
            message="Download started"
        )
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a video/audio file for processing"""
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        filename = f"{file_id}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "file_id": file_id,
            "filename": filename,
            "path": file_path,
            "size": os.path.getsize(file_path)
        }
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process/video", response_model=ProcessingResponse)
async def process_video(request: ProcessingRequest, background_tasks: BackgroundTasks):
    """Process video with various operations"""
    try:
        task_id = str(uuid.uuid4())
        
        # Start background processing task
        background_tasks.add_task(
            video_processor.process_video,
            request.input_path,
            task_id,
            request.operations
        )
        
        return ProcessingResponse(
            task_id=task_id,
            status="started",
            message="Video processing started"
        )
        
    except Exception as e:
        logger.error(f"Video processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process/audio", response_model=ProcessingResponse)
async def process_audio(request: ProcessingRequest, background_tasks: BackgroundTasks):
    """Process audio with various operations"""
    try:
        task_id = str(uuid.uuid4())
        
        # Start background processing task
        background_tasks.add_task(
            audio_processor.process_audio,
            request.input_path,
            task_id,
            request.operations
        )
        
        return ProcessingResponse(
            task_id=task_id,
            status="started",
            message="Audio processing started"
        )
        
    except Exception as e:
        logger.error(f"Audio processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get the status of a processing task"""
    try:
        # Check task status from various services
        status = await get_combined_task_status(task_id)
        return status
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{task_id}")
async def download_result(task_id: str):
    """Download the processed file"""
    try:
        # Find the processed file
        result_file = find_result_file(task_id)
        
        if not result_file or not os.path.exists(result_file):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            result_file,
            media_type='application/octet-stream',
            filename=os.path.basename(result_file)
        )
        
    except Exception as e:
        logger.error(f"Download result error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files")
async def list_files():
    """List all available files"""
    try:
        files = []
        
        # List uploaded files
        for file in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, file)
            files.append({
                "name": file,
                "path": file_path,
                "size": os.path.getsize(file_path),
                "type": "uploaded"
            })
        
        # List processed files
        for file in os.listdir(PROCESSED_DIR):
            file_path = os.path.join(PROCESSED_DIR, file)
            files.append({
                "name": file,
                "path": file_path,
                "size": os.path.getsize(file_path),
                "type": "processed"
            })
        
        return {"files": files}
        
    except Exception as e:
        logger.error(f"List files error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# AI Service Endpoints

@app.post("/ai/transcribe")
async def transcribe_audio(request: TranscriptionRequest, background_tasks: BackgroundTasks):
    """Transcribe audio to text using Whisper"""
    try:
        task_id = str(uuid.uuid4())
        
        background_tasks.add_task(
            stt_service.transcribe_audio,
            request.audio_path,
            request.language,
            request.model
        )
        
        return ProcessingResponse(
            task_id=task_id,
            status="started",
            message="Audio transcription started"
        )
        
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/translate")
async def translate_text(request: TranslationRequest):
    """Translate text using Google Translate"""
    try:
        result = await translation_service.translate_text(
            request.text,
            request.target_language,
            request.source_language
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/text-to-speech")
async def text_to_speech(request: TTSRequest, background_tasks: BackgroundTasks):
    """Convert text to speech using Google TTS or AWS Polly"""
    try:
        task_id = str(uuid.uuid4())
        output_path = os.path.join(PROCESSED_DIR, f"{task_id}_speech.mp3")
        
        background_tasks.add_task(
            tts_service.synthesize_speech,
            request.text,
            request.language,
            request.voice,
            "google",  # Default provider
            output_path
        )
        
        return ProcessingResponse(
            task_id=task_id,
            status="started",
            message="Text-to-speech conversion started"
        )
        
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/workflow", response_model=WorkflowResponse)
async def ai_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    """Execute complete AI workflow: download -> transcribe -> translate -> synthesize"""
    try:
        workflow_id = str(uuid.uuid4())
        
        # Determine input file
        input_file = None
        if request.input_url:
            # Download first
            download_task_id = str(uuid.uuid4())
            background_tasks.add_task(
                download_service.download_video,
                str(request.input_url),
                download_task_id
            )
            # Note: In a real implementation, we'd wait for download completion
            input_file = f"./videos/{download_task_id}_downloaded"
        elif request.input_file:
            input_file = request.input_file
        else:
            raise HTTPException(status_code=400, detail="Either input_url or input_file must be provided")
        
        # Start AI workflow
        background_tasks.add_task(
            ai_workflow_service.process_audio_workflow,
            input_file,
            request.parameters.get("target_language", "hi"),
            workflow_id
        )
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status="started",
            steps=[
                {"step": "download", "status": "started" if request.input_url else "skipped"},
                {"step": "transcribe", "status": "pending"},
                {"step": "translate", "status": "pending"},
                {"step": "synthesize", "status": "pending"}
            ],
            message="AI workflow started"
        )
        
    except Exception as e:
        logger.error(f"AI workflow error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/voices")
async def get_available_voices(provider: str = "google"):
    """Get available TTS voices"""
    try:
        voices = tts_service.get_available_voices(provider)
        return {"provider": provider, "voices": voices}
        
    except Exception as e:
        logger.error(f"Get voices error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/languages")
async def get_supported_languages():
    """Get supported translation languages"""
    try:
        languages = translation_service.get_supported_languages()
        return {"languages": languages}
        
    except Exception as e:
        logger.error(f"Get languages error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Storage Management Endpoints

@app.post("/storage/upload")
async def upload_to_storage(
    file_path: str,
    remote_key: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None
):
    """Upload a local file to storage (R2 or local)"""
    try:
        if not remote_key:
            # Generate remote key from file path
            remote_key = f"uploads/{Path(file_path).name}"
        
        result = await storage_manager.upload_file(file_path, remote_key, metadata)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Storage upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/storage/download/{remote_key:path}")
async def get_download_url(remote_key: str, expiration: int = 3600):
    """Get signed URL for file download"""
    try:
        result = await storage_manager.generate_signed_url(remote_key, expiration)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Download URL error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/storage/{remote_key:path}")
async def delete_from_storage(remote_key: str):
    """Delete file from storage"""
    try:
        result = await storage_manager.delete_file(remote_key)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Storage delete error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/storage/list")
async def list_storage_files(prefix: str = ""):
    """List files in storage"""
    try:
        result = await storage_manager.list_files(prefix)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Add storage type info
        result["storage_type"] = storage_manager.get_storage_type()
        
        return result
        
    except Exception as e:
        logger.error(f"Storage list error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/storage/info")
async def get_storage_info():
    """Get storage service information"""
    try:
        return {
            "storage_type": storage_manager.get_storage_type(),
            "r2_available": storage_manager.r2_service.is_available(),
            "bucket_name": storage_manager.r2_service.bucket_name if storage_manager.r2_service.is_available() else None
        }
        
    except Exception as e:
        logger.error(f"Storage info error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def get_combined_task_status(task_id: str) -> TaskStatus:
    """Get task status from all services"""
    # This would check Redis, Celery, or local task storage
    # For now, return a placeholder
    return TaskStatus(
        task_id=task_id,
        status="unknown",
        progress=0,
        message="Status check not implemented yet"
    )

def find_result_file(task_id: str) -> Optional[str]:
    """Find the result file for a given task ID"""
    # Search in processed directory
    for file in os.listdir(PROCESSED_DIR):
        if task_id in file:
            return os.path.join(PROCESSED_DIR, file)
    
    # Search in download directory
    for file in os.listdir(DOWNLOAD_DIR):
        if task_id in file:
            return os.path.join(DOWNLOAD_DIR, file)
    
    return None

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

