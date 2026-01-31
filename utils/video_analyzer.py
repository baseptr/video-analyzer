"""
Video Analyzer using Claude Vision API.

Analyzes videos for viral potential by extracting:
- Hook patterns
- Emotional triggers
- Pacing and structure
- Visual elements
- Timeline breakdown
"""

import os
import subprocess
import base64
import json
import re
import time
from typing import Optional, Dict
from utils.logger import setup_logger

logger = setup_logger(__name__)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def extract_video_frames(video_path: str, timestamps: list = None) -> list:
    """
    Extract frames from video using ffmpeg.

    Args:
        video_path: Path to video file
        timestamps: List of timestamps in seconds (default: [0, 3, 10])

    Returns:
        List of base64-encoded frame images
    """
    if timestamps is None:
        timestamps = [0, 3, 10]

    frames = []
    try:
        # Get duration
        duration_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        duration = float(subprocess.check_output(duration_cmd).decode().strip())

        # Adjust timestamps if video is shorter
        adjusted_timestamps = [min(t, duration - 0.1) for t in timestamps]

        for i, timestamp in enumerate(adjusted_timestamps):
            output_path = f"/tmp/frame_{i}_{int(timestamp)}s.png"

            extract_cmd = [
                "ffmpeg",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                output_path
            ]
            subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            with open(output_path, "rb") as f:
                frame_b64 = base64.b64encode(f.read()).decode('utf-8')
                frames.append({
                    "data": frame_b64,
                    "timestamp": timestamp,
                    "label": _get_frame_label(timestamp)
                })
            os.remove(output_path)

        logger.info(f"Extracted {len(frames)} frames at {timestamps}s")
        return frames
    except Exception as e:
        logger.error(f"Frame extraction failed: {e}")
        return []


def _get_frame_label(timestamp: float) -> str:
    """Get semantic label for frame based on timestamp."""
    if timestamp <= 1:
        return "hook"
    elif timestamp <= 5:
        return "transition"
    else:
        return "cta"


def analyze_video_with_claude(video_path: str) -> Optional[Dict]:
    """
    Analyze video using Claude Vision API.

    Returns patterns, viral probability, and recommendations.
    """
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set")
        return None

    # Handle R2 paths - download video first
    local_video_path = video_path
    cleanup_needed = False

    if video_path.startswith('r2://'):
        try:
            from utils.storage import get_storage
            import tempfile

            logger.info(f"Downloading video from R2: {video_path}")
            storage = get_storage()
            video_content = storage.get_file_content(video_path)

            if not video_content:
                logger.error(f"Failed to download video from R2: {video_path}")
                return None

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_file.write(video_content)
            temp_file.close()
            local_video_path = temp_file.name
            cleanup_needed = True
            logger.info(f"Video downloaded to: {local_video_path}")
        except Exception as e:
            logger.error(f"Failed to download R2 video: {e}")
            return None
    else:
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None
        logger.info(f"Analyzing local video: {video_path}")

    frames = extract_video_frames(local_video_path)

    # Cleanup temp file
    if cleanup_needed and os.path.exists(local_video_path):
        try:
            os.unlink(local_video_path)
            logger.info(f"Cleaned up temp file: {local_video_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file: {e}")

    if not frames:
        return None

    prompt = """Analyze this video from 3 key frames (Hook at 0s, Body at 3s, CTA at 10s) for VIRAL POTENTIAL.

Compare to successful viral videos and identify elements that drive:
1. Retention (keeping viewers watching)
2. Engagement (likes, comments, shares)
3. Shareability (why someone would share this)

Extract the following:

1. **hook_type**: (choose one)
   - **transformation**: Before/After result
   - **problem_solution**: Problem → Solution
   - **question**: Provocative question
   - **social_proof**: Testimonials, numbers, proof
   - **insider_secret**: Secret or insider tip
   - **urgency**: Time-limited urgency
   - **shock**: Surprising or unexpected opening

2. **emotion**: frustration, achievement, curiosity, trust, hope, fomo, empathy, excitement, neutral

3. **pacing**: fast, medium, slow

4. **content_style**: ugc, talking_head, screen_recording, animation, b_roll, mixed

5. **visual_elements**:
   - has_text_overlay: true/false
   - has_face: true/false
   - has_music: true/false (infer from context)
   - has_voiceover: true/false (infer from context)

6. **viral_probability**: 0.0 to 1.0 (based on hook strength, emotional impact, structure)

7. **predicted_engagement**: 0.0 to 1.0 (expected engagement rate)

8. **timeline** (breakdown by time):
   For each frame, specify:
   - **timestamp**: "0-3s" | "3-10s" | "10-15s"
   - **what_happens**: What's shown (text, visuals, actions)
   - **emotion_shift**: How viewer emotion changes
   - **retention_hook**: What keeps attention
   - **cta_presence**: Is there a call to action

9. **recommendations**: List of 3-5 specific improvements:
   - type: "hook" | "emotion" | "pacing" | "visual" | "cta"
   - suggestion: Specific actionable advice
   - expected_improvement: 0.0 to 0.5 (estimated impact)

10. **reasoning**: 2-3 sentences explaining your analysis

Respond ONLY in valid JSON format:
{
  "hook_type": "...",
  "emotion": "...",
  "pacing": "...",
  "content_style": "...",
  "has_text_overlay": true/false,
  "has_face": true/false,
  "has_music": true/false,
  "has_voiceover": true/false,
  "viral_probability": 0.0-1.0,
  "predicted_engagement": 0.0-1.0,
  "timeline": [
    {
      "timestamp": "0-3s",
      "what_happens": "...",
      "emotion_shift": "...",
      "retention_hook": "...",
      "cta_presence": false
    }
  ],
  "recommendations": [
    {
      "type": "hook",
      "suggestion": "...",
      "expected_improvement": 0.15
    }
  ],
  "reasoning": "..."
}"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        content = [{"type": "text", "text": prompt}]

        # Add frames with labels
        for frame in frames:
            frame_label = frame.get("label", "unknown")
            timestamp = frame.get("timestamp", 0)

            content.append({
                "type": "text",
                "text": f"\n[Frame at {timestamp}s - {frame_label.upper()}]:"
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": frame["data"]
                }
            })

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": content}]
        )

        response_text = response.content[0].text
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        result = json.loads(json_match.group(1) if json_match else response_text)

        logger.info(f"Claude analyzed: hook={result.get('hook_type')}, viral_prob={result.get('viral_probability', 0):.2%}")
        return result

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return None


def analyze_video_with_retry(video_path: str, max_retries: int = 3) -> Dict:
    """Analyze with retries."""
    for attempt in range(max_retries):
        result = analyze_video_with_claude(video_path)
        if result:
            return result
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)

    return {
        "hook_type": "unknown",
        "emotion": "unknown",
        "pacing": "medium",
        "content_style": "unknown",
        "has_text_overlay": False,
        "has_face": False,
        "has_music": False,
        "has_voiceover": False,
        "viral_probability": 0.0,
        "predicted_engagement": 0.0,
        "timeline": [],
        "recommendations": [],
        "reasoning": "Analysis failed - video file not found or Claude API error"
    }
