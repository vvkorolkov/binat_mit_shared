# binat_mit_shared

**Reusable tools by BINAT.US**  
MIT-licensed Python utilities for working with media files and video metadata.

## 📦 Installation

Install directly from GitHub:

    pip install git+https://github.com/vvkorolkov/binat_mit_shared.git

## 📁 Modules

### VideoHelper

A utility class to work with video metadata using ffprobe. Includes FPS detection, frame/time conversion, and metadata flattening.

## 🧪 Example usage

### Basic metadata extraction

```python
from binat_shared.video_helper import VideoHelper

video_path = "example.mp4"
ffprobe_data = VideoHelper.get_ffprobe_output(video_path)

duration = VideoHelper.get_duration_seconds(ffprobe_data)
fps = VideoHelper.get_fps(ffprobe_data)
frame_count = VideoHelper.get_duration_frames(ffprobe_data)

print(f"Duration: {duration:.2f} sec, FPS: {fps:.2f}, Frames: {frame_count}")
```

### Convert timestamp to frame

```python
frame_number, formatted_time = VideoHelper.convert_timestamp_to_frame("00:02:10.500", fps)
print(f"Timestamp maps to frame: {frame_number}, Time: {formatted_time}")
```

### Convert millisecond position to frame

```python
frame_number, formatted_time = VideoHelper.convert_position_to_frame(90250, fps)
print(f"Position maps to frame: {frame_number}, Time: {formatted_time}")
```

### Flatten nested ffprobe metadata

```python
flat = VideoHelper.flatten_dict(ffprobe_data)
for key, value in flat.items():
    print(f"{key}: {value}")
```

## ⚠️ Requirements

You must have `ffprobe` available in your system PATH.

Install via:

**macOS (Homebrew):**

    brew install ffmpeg

**Ubuntu/Debian:**

    sudo apt install ffmpeg

## 📄 License

MIT License — see LICENSE for details.

## 🔁 Version

To check which version of the module is in use:

```python
version, comment = VideoHelper.get_version()
print(f"Version: {version} ({comment})")
```