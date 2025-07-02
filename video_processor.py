import os
import logging
import ffmpeg
from typing import Dict, Any, List, Optional
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Service for video processing using FFmpeg"""
    
    def __init__(self, output_dir: str = "./processed"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    async def process_video(
        self, 
        input_path: str, 
        task_id: str, 
        operations: List[str],
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process video with specified operations"""
        try:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Input file not found: {input_path}")
            
            logger.info(f"Starting video processing for task {task_id}")
            
            if parameters is None:
                parameters = {}
            
            current_input = input_path
            
            for i, operation in enumerate(operations):
                output_path = self._get_output_path(task_id, operation, i)
                
                if operation == "extract_audio":
                    current_input = await self._extract_audio(current_input, output_path, parameters)
                elif operation == "convert_format":
                    current_input = await self._convert_format(current_input, output_path, parameters)
                elif operation == "resize_video":
                    current_input = await self._resize_video(current_input, output_path, parameters)
                elif operation == "trim_video":
                    current_input = await self._trim_video(current_input, output_path, parameters)
                elif operation == "add_subtitles":
                    current_input = await self._add_subtitles(current_input, output_path, parameters)
                else:
                    logger.warning(f"Unknown operation: {operation}")
                    continue
            
            # Get final file info
            file_info = self._get_file_info(current_input)
            
            result = {
                'task_id': task_id,
                'status': 'completed',
                'output_path': current_input,
                'operations_performed': operations,
                'file_info': file_info
            }
            
            logger.info(f"Video processing completed for task {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Video processing failed for task {task_id}: {str(e)}")
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    async def _extract_audio(self, input_path: str, output_path: str, params: Dict[str, Any]) -> str:
        """Extract audio from video"""
        try:
            audio_format = params.get('audio_format', 'mp3')
            audio_quality = params.get('audio_quality', '192k')
            
            # Use output_path with correct extension
            output_path = output_path.replace('.mp4', f'.{audio_format}')
            
            (
                ffmpeg
                .input(input_path)
                .output(output_path, acodec='libmp3lame' if audio_format == 'mp3' else 'aac', 
                       audio_bitrate=audio_quality)
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Audio extracted to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Audio extraction failed: {str(e)}")
            raise
    
    async def _convert_format(self, input_path: str, output_path: str, params: Dict[str, Any]) -> str:
        """Convert video format"""
        try:
            target_format = params.get('target_format', 'mp4')
            video_codec = params.get('video_codec', 'libx264')
            audio_codec = params.get('audio_codec', 'aac')
            
            # Update output path extension
            output_path = Path(output_path).with_suffix(f'.{target_format}')
            
            (
                ffmpeg
                .input(input_path)
                .output(str(output_path), vcodec=video_codec, acodec=audio_codec)
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Format converted to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Format conversion failed: {str(e)}")
            raise
    
    async def _resize_video(self, input_path: str, output_path: str, params: Dict[str, Any]) -> str:
        """Resize video resolution"""
        try:
            width = params.get('width', 1280)
            height = params.get('height', 720)
            
            (
                ffmpeg
                .input(input_path)
                .filter('scale', width, height)
                .output(output_path)
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Video resized to {width}x{height}: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Video resize failed: {str(e)}")
            raise
    
    async def _trim_video(self, input_path: str, output_path: str, params: Dict[str, Any]) -> str:
        """Trim video to specified duration"""
        try:
            start_time = params.get('start_time', 0)  # seconds
            duration = params.get('duration', 30)     # seconds
            
            (
                ffmpeg
                .input(input_path, ss=start_time, t=duration)
                .output(output_path)
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Video trimmed from {start_time}s for {duration}s: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Video trim failed: {str(e)}")
            raise
    
    async def _add_subtitles(self, input_path: str, output_path: str, params: Dict[str, Any]) -> str:
        """Add subtitles to video"""
        try:
            subtitle_path = params.get('subtitle_path')
            if not subtitle_path or not os.path.exists(subtitle_path):
                logger.warning("Subtitle file not found, skipping subtitle addition")
                return input_path
            
            (
                ffmpeg
                .input(input_path)
                .output(output_path, vf=f"subtitles={subtitle_path}")
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Subtitles added: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Subtitle addition failed: {str(e)}")
            raise
    
    def _get_output_path(self, task_id: str, operation: str, step: int) -> str:
        """Generate output path for processing step"""
        filename = f"{task_id}_{operation}_{step}.mp4"
        return os.path.join(self.output_dir, filename)
    
    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about a video file"""
        try:
            probe = ffmpeg.probe(file_path)
            
            video_stream = next((stream for stream in probe['streams'] 
                               if stream['codec_type'] == 'video'), None)
            audio_stream = next((stream for stream in probe['streams'] 
                               if stream['codec_type'] == 'audio'), None)
            
            info = {
                'duration': float(probe['format']['duration']),
                'size': int(probe['format']['size']),
                'format': probe['format']['format_name'],
                'bitrate': int(probe['format']['bit_rate'])
            }
            
            if video_stream:
                info.update({
                    'width': int(video_stream['width']),
                    'height': int(video_stream['height']),
                    'video_codec': video_stream['codec_name'],
                    'fps': eval(video_stream['r_frame_rate'])
                })
            
            if audio_stream:
                info.update({
                    'audio_codec': audio_stream['codec_name'],
                    'sample_rate': int(audio_stream['sample_rate']),
                    'channels': int(audio_stream['channels'])
                })
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return {'error': str(e)}
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported video formats"""
        return ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', '3gp']
    
    def get_supported_operations(self) -> List[str]:
        """Get list of supported operations"""
        return [
            'extract_audio',
            'convert_format', 
            'resize_video',
            'trim_video',
            'add_subtitles'
        ]

