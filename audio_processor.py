import os
import logging
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path
import ffmpeg

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Service for audio processing using SoX and FFmpeg"""
    
    def __init__(self, output_dir: str = "./processed"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    async def process_audio(
        self, 
        input_path: str, 
        task_id: str, 
        operations: List[str],
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process audio with specified operations"""
        try:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Input file not found: {input_path}")
            
            logger.info(f"Starting audio processing for task {task_id}")
            
            if parameters is None:
                parameters = {}
            
            current_input = input_path
            
            for i, operation in enumerate(operations):
                output_path = self._get_output_path(task_id, operation, i)
                
                if operation == "noise_reduction":
                    current_input = await self._noise_reduction(current_input, output_path, parameters)
                elif operation == "normalize_audio":
                    current_input = await self._normalize_audio(current_input, output_path, parameters)
                elif operation == "change_speed":
                    current_input = await self._change_speed(current_input, output_path, parameters)
                elif operation == "extract_segments":
                    current_input = await self._extract_segments(current_input, output_path, parameters)
                else:
                    logger.warning(f"Unknown operation: {operation}")
                    continue
            
            # Get final file info
            file_info = self._get_audio_info(current_input)
            
            result = {
                'task_id': task_id,
                'status': 'completed',
                'output_path': current_input,
                'operations_performed': operations,
                'file_info': file_info
            }
            
            logger.info(f"Audio processing completed for task {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Audio processing failed for task {task_id}: {str(e)}")
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    async def _noise_reduction(self, input_path: str, output_path: str, params: Dict[str, Any]) -> str:
        """Apply noise reduction using SoX"""
        try:
            # SoX noise reduction parameters
            noise_factor = params.get('noise_factor', 0.21)
            
            # Create noise profile first (using first 0.5 seconds)
            noise_profile = output_path.replace('.wav', '_noise.prof')
            
            # Extract noise sample
            cmd_noise = [
                'sox', input_path, '-n', 'trim', '0', '0.5', 'noiseprof', noise_profile
            ]
            subprocess.run(cmd_noise, check=True, capture_output=True)
            
            # Apply noise reduction
            cmd_reduce = [
                'sox', input_path, output_path, 'noisered', noise_profile, str(noise_factor)
            ]
            subprocess.run(cmd_reduce, check=True, capture_output=True)
            
            # Clean up noise profile
            if os.path.exists(noise_profile):
                os.remove(noise_profile)
            
            logger.info(f"Noise reduction applied: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"SoX noise reduction failed: {e.stderr.decode()}")
            # Fallback to FFmpeg high-pass filter
            return await self._fallback_noise_reduction(input_path, output_path)
        except Exception as e:
            logger.error(f"Noise reduction failed: {str(e)}")
            raise
    
    async def _fallback_noise_reduction(self, input_path: str, output_path: str) -> str:
        """Fallback noise reduction using FFmpeg"""
        try:
            (
                ffmpeg
                .input(input_path)
                .filter('highpass', f=200)  # Remove low-frequency noise
                .filter('lowpass', f=8000)  # Remove high-frequency noise
                .output(output_path)
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Fallback noise reduction applied: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Fallback noise reduction failed: {str(e)}")
            raise
    
    async def _normalize_audio(self, input_path: str, output_path: str, params: Dict[str, Any]) -> str:
        """Normalize audio levels"""
        try:
            target_level = params.get('target_level', -3.0)  # dB
            
            # Use FFmpeg loudnorm filter for better normalization
            (
                ffmpeg
                .input(input_path)
                .filter('loudnorm', I=-16, LRA=11, TP=-1.5)
                .output(output_path)
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Audio normalized: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Audio normalization failed: {str(e)}")
            # Fallback to simple volume adjustment
            return await self._fallback_normalize(input_path, output_path, params)
    
    async def _fallback_normalize(self, input_path: str, output_path: str, params: Dict[str, Any]) -> str:
        """Fallback normalization using volume filter"""
        try:
            volume_level = params.get('volume_level', 1.5)
            
            (
                ffmpeg
                .input(input_path)
                .filter('volume', volume_level)
                .output(output_path)
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Fallback normalization applied: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Fallback normalization failed: {str(e)}")
            raise
    
    async def _change_speed(self, input_path: str, output_path: str, params: Dict[str, Any]) -> str:
        """Change audio playback speed"""
        try:
            speed_factor = params.get('speed_factor', 1.0)
            preserve_pitch = params.get('preserve_pitch', True)
            
            if preserve_pitch:
                # Use atempo filter to preserve pitch
                (
                    ffmpeg
                    .input(input_path)
                    .filter('atempo', speed_factor)
                    .output(output_path)
                    .overwrite_output()
                    .run(quiet=True)
                )
            else:
                # Change speed and pitch together
                (
                    ffmpeg
                    .input(input_path)
                    .filter('asetrate', f'44100*{speed_factor}')
                    .filter('aresample', 44100)
                    .output(output_path)
                    .overwrite_output()
                    .run(quiet=True)
                )
            
            logger.info(f"Speed changed by factor {speed_factor}: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Speed change failed: {str(e)}")
            raise
    
    async def _extract_segments(self, input_path: str, output_path: str, params: Dict[str, Any]) -> str:
        """Extract specific audio segments"""
        try:
            segments = params.get('segments', [{'start': 0, 'duration': 30}])
            
            if len(segments) == 1:
                # Single segment
                segment = segments[0]
                start_time = segment.get('start', 0)
                duration = segment.get('duration', 30)
                
                (
                    ffmpeg
                    .input(input_path, ss=start_time, t=duration)
                    .output(output_path)
                    .overwrite_output()
                    .run(quiet=True)
                )
                
                logger.info(f"Audio segment extracted: {output_path}")
                return output_path
            else:
                # Multiple segments - concatenate them
                segment_files = []
                
                for i, segment in enumerate(segments):
                    segment_path = output_path.replace('.wav', f'_segment_{i}.wav')
                    start_time = segment.get('start', 0)
                    duration = segment.get('duration', 30)
                    
                    (
                        ffmpeg
                        .input(input_path, ss=start_time, t=duration)
                        .output(segment_path)
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    segment_files.append(segment_path)
                
                # Concatenate segments
                inputs = [ffmpeg.input(f) for f in segment_files]
                (
                    ffmpeg
                    .concat(*inputs, v=0, a=1)
                    .output(output_path)
                    .overwrite_output()
                    .run(quiet=True)
                )
                
                # Clean up segment files
                for f in segment_files:
                    if os.path.exists(f):
                        os.remove(f)
                
                logger.info(f"Multiple audio segments extracted and concatenated: {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"Segment extraction failed: {str(e)}")
            raise
    
    def _get_output_path(self, task_id: str, operation: str, step: int) -> str:
        """Generate output path for processing step"""
        filename = f"{task_id}_{operation}_{step}.wav"
        return os.path.join(self.output_dir, filename)
    
    def _get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about an audio file"""
        try:
            probe = ffmpeg.probe(file_path)
            
            audio_stream = next((stream for stream in probe['streams'] 
                               if stream['codec_type'] == 'audio'), None)
            
            info = {
                'duration': float(probe['format']['duration']),
                'size': int(probe['format']['size']),
                'format': probe['format']['format_name'],
                'bitrate': int(probe['format']['bit_rate'])
            }
            
            if audio_stream:
                info.update({
                    'codec': audio_stream['codec_name'],
                    'sample_rate': int(audio_stream['sample_rate']),
                    'channels': int(audio_stream['channels']),
                    'bit_depth': audio_stream.get('bits_per_sample', 'unknown')
                })
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting audio info: {str(e)}")
            return {'error': str(e)}
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats"""
        return ['wav', 'mp3', 'flac', 'aac', 'ogg', 'm4a', 'wma']
    
    def get_supported_operations(self) -> List[str]:
        """Get list of supported audio operations"""
        return [
            'noise_reduction',
            'normalize_audio',
            'change_speed',
            'extract_segments'
        ]

