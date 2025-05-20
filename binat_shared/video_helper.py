# binat_shared/video_helper.py
import shutil
import subprocess
import json
import os
import re
import logging

__version__ = "0.0.7"

class VideoHelper:

    @staticmethod
    def get_version():
        return __version__

    @staticmethod
    def _resolve_binary_path(env_var: str, binary_name: str) -> str:
        env_override = os.environ.get(env_var)
        if env_override:
            return env_override
        path = shutil.which(binary_name)
        if not path:
            raise RuntimeError(f"{binary_name} not found in system PATH and {env_var} not set.")
        return path

    @staticmethod
    def get_ffprobe_path() -> str:
        return VideoHelper._resolve_binary_path("FFPROBE_PATH", "ffprobe")

    @staticmethod
    def get_ffmpeg_path() -> str:
        return VideoHelper._resolve_binary_path("FFMPEG_PATH", "ffmpeg")

    @staticmethod
    def get_ffprobe_output(file_path):
        ffprobe_path = VideoHelper.get_ffprobe_path()
        if not os.path.exists(ffprobe_path):
            logging.error(f"Error: ffprobe not found at {ffprobe_path}")
            return None

        try:
            cmd = [
                ffprobe_path,
                "-v", "error",
                "-show_entries", "format:streams",
                "-print_format", "json",
                file_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return json.loads(result.stdout)
        except Exception as e:
            logging.error(f"Error running ffprobe: {e}")
            return None

    @staticmethod
    def get_duration_seconds(ffprobe_data):
        try:
            return float(ffprobe_data['format']['duration'])
        except (KeyError, TypeError):
            logging.error("Could not extract video duration in seconds.")
            return 0.0

    @staticmethod
    def get_fps(ffprobe_data):
        try:
            duration = float(ffprobe_data['format']['duration'])
            nb_frames = next(
                (int(stream['nb_frames']) for stream in ffprobe_data['streams'] if stream['codec_type'] == 'video'),
                None
            )
            if nb_frames:
                return nb_frames / duration
        except Exception as e:
            logging.warning(f"Could not compute fps from nb_frames: {e}")
        try:
            video_stream = next(
                (stream for stream in ffprobe_data['streams'] if stream['codec_type'] == 'video'), None
            )
            return eval(video_stream.get('r_frame_rate', '0/1'))
        except Exception as e:
            logging.error(f"Fallback FPS failed: {e}")
            return 0.0

    @staticmethod
    def get_duration_frames(ffprobe_data):
        video_stream = next(stream for stream in ffprobe_data['streams'] if stream['codec_type'] == 'video')
        return int(video_stream['nb_frames'])

    @staticmethod
    def flatten_dict(data, parent_key='', sep='.'):
        items = []
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(VideoHelper.flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    list_key = f"{new_key}[{i}]"
                    if isinstance(item, dict):
                        items.extend(VideoHelper.flatten_dict(item, list_key, sep=sep).items())
                    else:
                        items.append((list_key, item))
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def convert_timestamp_to_frame(timestamp: str, fps: float) -> tuple[int, str]:
        if not isinstance(timestamp, str):
            raise ValueError(f"Expected string for timestamp, got {type(timestamp)}")
        if not re.match(r"^\d{2}:\d{2}:\d{2}(\.\d+)?$", timestamp):
            raise ValueError(f"Invalid timestamp format: {timestamp}")
        try:
            h, m, s = timestamp.split(":")
            seconds = int(h) * 3600 + int(m) * 60 + float(s)
            frame_number = max(int(round(seconds * fps)), 0)
            formatted_time = f"{int(h):02}:{int(m):02}:{float(s):06.3f}"
            return frame_number, formatted_time
        except Exception as e:
            raise ValueError(f"Error parsing timestamp '{timestamp}': {e}")

    @staticmethod
    def convert_position_to_frame(position_ms: float, fps: float) -> tuple[int, str]:
        if not isinstance(position_ms, (int, float)):
            raise ValueError(f"Expected float or int for position_ms, got {type(position_ms)}")
        try:
            seconds = position_ms / 1000.0
            frame_number = max(int(seconds * fps), 0)
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = seconds % 60
            formatted_time = f"{h:02}:{m:02}:{s:06.3f}"
            return frame_number, formatted_time
        except Exception as e:
            raise ValueError(f"Error converting position '{position_ms}' to frame: {e}")

    @staticmethod
    def get_video_orientation(ffprobe_data):
        video_stream = next((stream for stream in ffprobe_data['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream:
            return "Unknown", 0

        # Check for rotation
        rotation = None
        for side_data in video_stream.get("side_data_list", []):
            if side_data.get("side_data_type") == "Display Matrix":
                rotation = side_data.get("rotation")

        if rotation is not None:
            if rotation == 0:
                return "Horizontal", 0
            elif rotation in [-90, 90]:
                return "Vertical", rotation

        # Fallback to width/height
        width = video_stream.get("width", 0)
        height = video_stream.get("height", 0)
        return ("Horizontal", 0) if width > height else ("Vertical", 0)

    @staticmethod
    def is_video_file_valid(path: str) -> tuple[bool, str]:
        import subprocess
        try:
            result = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"],
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                timeout=15
            )
            stderr_output = result.stderr.decode("utf-8").strip()
            return (result.returncode == 0 and not stderr_output), stderr_output
        except Exception as e:
            return False, str(e)
