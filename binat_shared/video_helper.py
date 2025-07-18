# binat_shared/video_helper.py
import shutil
import subprocess
import json
import os
import logging

__version__ = "0.0.13"

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
        try:
            video_stream = next(stream for stream in ffprobe_data['streams'] if stream.get('codec_type') == 'video')
            nb_frames = video_stream.get('nb_frames')
            return int(nb_frames) if nb_frames is not None else None
        except (StopIteration, ValueError, TypeError):
            return None

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
        ts = timestamp.strip().replace(",", ".")
        try:
            parts = ts.split(":")
            if len(parts) > 3:
                raise ValueError("Too many parts in timestamp")
            parts = [float(p) for p in parts]
            while len(parts) < 3:
                parts.insert(0, 0.0)
            h, m, s = parts[-3], parts[-2], parts[-1]
            total_seconds = h * 3600 + m * 60 + s
            frame_number = max(int(round(total_seconds * fps)), 0)
            formatted_time = f"{int(h):02}:{int(m):02}:{s:06.3f}"
            return frame_number, formatted_time
        except Exception as e:
            raise ValueError(f"Invalid timestamp '{timestamp}': {e}")

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
        try:
            ffprobe_path = VideoHelper.get_ffprobe_path()
            result = subprocess.run(
                [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of",
                 "default=noprint_wrappers=1:nokey=1", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15
            )
            output = result.stdout.strip()
            error_output = result.stderr.strip()
            is_valid = result.returncode == 0 and output and float(output) > 0
            return is_valid, error_output or output
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_container_format(path: str) -> str:
        import os
        ext = os.path.splitext(path)[1].lower()
        return ext

    @staticmethod
    def get_pixel_format(ffprobe_data):
        pix_fmt = ffprobe_data['streams'][0].get("pix_fmt", None)
        return pix_fmt

    @staticmethod
    def get_bit_depth(ffprobe_data):
        bit_depth = ffprobe_data['streams'][0].get("bits_per_raw_sample", None)
        return bit_depth

    @staticmethod
    def get_width(ffprobe_data):
        for stream in ffprobe_data.get('streams', []):
            if stream.get('codec_type') == 'video':
                width = stream.get('width')
                if width is not None:
                    return int(width)
        raise ValueError("Video width could not be determined from ffprobe data.")

    @staticmethod
    def get_height(ffprobe_data):
        for stream in ffprobe_data.get('streams', []):
            if stream.get('codec_type') == 'video':
                height = stream.get('height')
                if height is not None:
                    return int(height)
        raise ValueError("Video height could not be determined from ffprobe data.")