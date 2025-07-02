import os
import logging
from typing import Optional, Dict, Any
from yt_dlp import YoutubeDL
from pathlib import Path

logger = logging.getLogger(__name__)

class DownloadService:
    """Service for downloading videos from various platforms"""
    
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
    
    async def download_video(
        self, 
        url: str, 
        task_id: str, 
        format_preference: str = "best"
    ) -> Dict[str, Any]:
        """Download video from URL"""
        try:
            logger.info(f"Starting download for task {task_id}: {url}")
            
            # Configure yt-dlp options
            ydl_opts = {
                'outtmpl': f'{self.download_dir}/{task_id}_%(title)s.%(ext)s',
                'format': self._get_format_selector(format_preference),
                'noplaylist': True,
                'quiet': False,
                'no_warnings': False,
                'extractaudio': False,
                'audioformat': 'mp3',
                'embed_subs': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=False)
                
                # Download the video
                ydl.download([url])
                
                # Find the downloaded file
                downloaded_file = self._find_downloaded_file(task_id, info)
                
                result = {
                    'task_id': task_id,
                    'status': 'completed',
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'file_path': downloaded_file,
                    'file_size': os.path.getsize(downloaded_file) if downloaded_file else 0,
                    'format': info.get('ext', 'unknown')
                }
                
                logger.info(f"Download completed for task {task_id}")
                return result
                
        except Exception as e:
            logger.error(f"Download failed for task {task_id}: {str(e)}")
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _get_format_selector(self, format_preference: str) -> str:
        """Get format selector for yt-dlp"""
        format_map = {
            'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'worst': 'worst',
            'audio': 'bestaudio/best',
            'mp4': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'webm': 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]',
            '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]'
        }
        
        return format_map.get(format_preference, format_map['best'])
    
    def _find_downloaded_file(self, task_id: str, info: Dict[str, Any]) -> Optional[str]:
        """Find the downloaded file by task ID"""
        try:
            # Look for files with task_id in the name
            for file in os.listdir(self.download_dir):
                if task_id in file:
                    return os.path.join(self.download_dir, file)
            
            # Fallback: look for files with similar title
            title = info.get('title', '').replace(' ', '_')[:50]  # Truncate long titles
            for file in os.listdir(self.download_dir):
                if title.lower() in file.lower():
                    return os.path.join(self.download_dir, file)
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding downloaded file: {str(e)}")
            return None
    
    def get_download_info(self, url: str) -> Dict[str, Any]:
        """Get information about a video without downloading"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0),
                    'formats': [
                        {
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext'),
                            'resolution': f.get('resolution'),
                            'filesize': f.get('filesize')
                        }
                        for f in info.get('formats', [])
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            return {'error': str(e)}
    
    def list_downloads(self) -> list:
        """List all downloaded files"""
        try:
            files = []
            for file in os.listdir(self.download_dir):
                file_path = os.path.join(self.download_dir, file)
                if os.path.isfile(file_path):
                    files.append({
                        'name': file,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'modified': os.path.getmtime(file_path)
                    })
            
            return sorted(files, key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing downloads: {str(e)}")
            return []

