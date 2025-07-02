from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class ProcessingOperation(str, Enum):
    """Available processing operations"""
    # Video operations
    EXTRACT_AUDIO = "extract_audio"
    CONVERT_FORMAT = "convert_format"
    RESIZE_VIDEO = "resize_video"
    TRIM_VIDEO = "trim_video"
    ADD_SUBTITLES = "add_subtitles"
    
    # Audio operations
    NOISE_REDUCTION = "noise_reduction"
    NORMALIZE_AUDIO = "normalize_audio"
    CHANGE_SPEED = "change_speed"
    EXTRACT_SEGMENTS = "extract_segments"
    
    # AI operations
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"
    TEXT_TO_SPEECH = "text_to_speech"

class TaskStatusEnum(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    STARTED = "started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DownloadRequest(BaseModel):
    """Request model for video download"""
    url: HttpUrl = Field(..., description="URL to download from")
    format_preference: Optional[str] = Field("best", description="Format preference (best, worst, mp4, etc.)")
    quality: Optional[str] = Field("720p", description="Video quality preference")
    audio_only: Optional[bool] = Field(False, description="Download audio only")

class ProcessingRequest(BaseModel):
    """Request model for video/audio processing"""
    input_path: str = Field(..., description="Path to input file")
    operations: List[ProcessingOperation] = Field(..., description="List of operations to perform")
    output_format: Optional[str] = Field("mp4", description="Output format")
    parameters: Optional[Dict[str, Any]] = Field({}, description="Additional parameters for operations")

class ProcessingResponse(BaseModel):
    """Response model for processing requests"""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatusEnum = Field(..., description="Current task status")
    message: str = Field(..., description="Status message")
    estimated_time: Optional[int] = Field(None, description="Estimated completion time in seconds")

class TaskStatus(BaseModel):
    """Task status model"""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatusEnum = Field(..., description="Current task status")
    progress: int = Field(0, ge=0, le=100, description="Progress percentage")
    message: str = Field("", description="Current status message")
    result_path: Optional[str] = Field(None, description="Path to result file if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: Optional[str] = Field(None, description="Task creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

class TranscriptionRequest(BaseModel):
    """Request model for audio transcription"""
    audio_path: str = Field(..., description="Path to audio file")
    language: Optional[str] = Field("auto", description="Source language (auto-detect if not specified)")
    model: Optional[str] = Field("base", description="Whisper model size (tiny, base, small, medium, large)")

class TranslationRequest(BaseModel):
    """Request model for text translation"""
    text: str = Field(..., description="Text to translate")
    source_language: Optional[str] = Field("auto", description="Source language")
    target_language: str = Field(..., description="Target language")

class TTSRequest(BaseModel):
    """Request model for text-to-speech"""
    text: str = Field(..., description="Text to convert to speech")
    language: str = Field("en", description="Language code")
    voice: Optional[str] = Field("default", description="Voice selection")
    speed: Optional[float] = Field(1.0, ge=0.5, le=2.0, description="Speech speed multiplier")

class FileInfo(BaseModel):
    """File information model"""
    name: str = Field(..., description="File name")
    path: str = Field(..., description="File path")
    size: int = Field(..., description="File size in bytes")
    type: str = Field(..., description="File type")
    duration: Optional[float] = Field(None, description="Duration in seconds for media files")
    format: Optional[str] = Field(None, description="File format")
    created_at: Optional[str] = Field(None, description="Creation timestamp")

class WorkflowRequest(BaseModel):
    """Request model for workflow automation"""
    input_url: Optional[HttpUrl] = Field(None, description="Input URL to download")
    input_file: Optional[str] = Field(None, description="Input file path")
    workflow_steps: List[ProcessingOperation] = Field(..., description="Sequence of operations")
    output_format: Optional[str] = Field("mp4", description="Final output format")
    parameters: Optional[Dict[str, Any]] = Field({}, description="Parameters for each step")

class WorkflowResponse(BaseModel):
    """Response model for workflow requests"""
    workflow_id: str = Field(..., description="Unique workflow identifier")
    status: TaskStatusEnum = Field(..., description="Workflow status")
    steps: List[Dict[str, Any]] = Field(..., description="Individual step statuses")
    message: str = Field(..., description="Status message")

