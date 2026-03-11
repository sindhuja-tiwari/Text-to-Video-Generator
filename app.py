"""
Text-to-Video Generator Backend — CORRECTED VERSION
Uses: bytedance/seedance-1-lite on Replicate (2.7M+ runs, actively maintained)

Model page: https://replicate.com/bytedance/seedance-1-lite
Generates: real MP4 videos, 5s or 10s, 480p or 720p

Setup:
    pip install flask flask-cors replicate python-dotenv

    Create .env file:
        REPLICATE_API_TOKEN=r8_your_token_here

Run:
    python app.py
"""

import os
import time
import replicate
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

# ─────────────────────────────────────────────────────────
# Model: bytedance/seedance-1-lite
# - NO version hash needed (use latest automatically)
# - Supports text-to-video and image-to-video
# - Outputs real MP4 files at 480p or 720p
# - 5s or 10s duration options
# ─────────────────────────────────────────────────────────
MODEL = "bytedance/seedance-1-lite"


@app.route("/health", methods=["GET"])
def health():
    has_token = bool(REPLICATE_API_TOKEN)
    return jsonify({
        "status": "ok",
        "model": MODEL,
        "token_set": has_token
    })


@app.route("/generate", methods=["POST"])
def generate_video():
    """
    POST /generate
    Required body fields:
        prompt      (str)  — text description of the video

    Optional body fields:
        duration    (int)  — 5 or 10  (default: 5)
        resolution  (str)  — "480p" or "720p"  (default: "720p")
        aspect_ratio (str) — "16:9", "9:16", or "1:1"  (default: "16:9")
        fps         (int)  — 24 (default)
        camera_fixed (bool) — False (default)
        seed        (int)  — for reproducibility (optional)

    Returns:
        { "success": true, "video_url": "https://...", "elapsed_seconds": 45.2 }
    """
    if not REPLICATE_API_TOKEN:
        return jsonify({
            "success": False,
            "error": "REPLICATE_API_TOKEN not set. Create a .env file with your token from replicate.com."
        }), 500

    data = request.get_json(force=True)
    if not data or not data.get("prompt", "").strip():
        return jsonify({"success": False, "error": "Missing required field: 'prompt'"}), 400

    prompt       = data["prompt"].strip()
    duration     = int(data.get("duration", 5))
    resolution   = data.get("resolution", "720p")
    aspect_ratio = data.get("aspect_ratio", "16:9")
    fps          = int(data.get("fps", 24))
    camera_fixed = bool(data.get("camera_fixed", False))
    seed         = data.get("seed")  # None = random

    # Validate params
    if duration not in (5, 10):
        duration = 5
    if resolution not in ("480p", "720p"):
        resolution = "720p"
    if aspect_ratio not in ("16:9", "9:16", "1:1"):
        aspect_ratio = "16:9"

    print(f"\n[generate] prompt='{prompt[:80]}'")
    print(f"[generate] duration={duration}s resolution={resolution} aspect={aspect_ratio}")

    try:
        client = replicate.Client(api_token=REPLICATE_API_TOKEN)
        start = time.time()

        # Build input — only include seed if provided
        model_input = {
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "fps": fps,
            "camera_fixed": camera_fixed,
        }
        if seed is not None:
            model_input["seed"] = int(seed)

        output = client.run(MODEL, input=model_input)

        elapsed = round(time.time() - start, 1)

        # seedance-1-lite returns a single URL string
        video_url = str(output)

        print(f"[generate] ✓ Done in {elapsed}s → {video_url[:80]}...")

        return jsonify({
            "success": True,
            "video_url": video_url,
            "elapsed_seconds": elapsed,
            "prompt": prompt,
            "settings": {
                "duration": duration,
                "resolution": resolution,
                "aspect_ratio": aspect_ratio,
                "fps": fps
            }
        })

    except replicate.exceptions.ReplicateError as e:
        msg = str(e)
        print(f"[generate] ✗ Replicate error: {msg}")
        # Give user-friendly messages for common errors
        if "authentication" in msg.lower() or "token" in msg.lower():
            msg = "Invalid API token. Check your REPLICATE_API_TOKEN in .env"
        elif "nsfw" in msg.lower():
            msg = "Prompt flagged as NSFW. Please try a different prompt."
        elif "quota" in msg.lower() or "credit" in msg.lower():
            msg = "Replicate account out of credits. Add credits at replicate.com/account/billing"
        return jsonify({"success": False, "error": msg}), 500

    except Exception as e:
        msg = str(e)
        print(f"[generate] ✗ Unexpected error: {msg}")
        return jsonify({"success": False, "error": msg}), 500


@app.route("/models", methods=["GET"])
def list_models():
    """Returns info on the models available in this API."""
    return jsonify({
        "active_model": MODEL,
        "models": [
            {
                "id": "seedance-1-lite",
                "replicate_id": "bytedance/seedance-1-lite",
                "name": "Seedance 1 Lite",
                "description": "ByteDance's fast text-to-video model. Generates real MP4s at 480p/720p.",
                "durations": [5, 10],
                "resolutions": ["480p", "720p"],
                "aspect_ratios": ["16:9", "9:16", "1:1"],
                "avg_time_seconds": "30-90"
            }
        ]
    })


if __name__ == "__main__":
    print("=" * 55)
    print("  Text-to-Video API — bytedance/seedance-1-lite")
    print(f"  Token set: {'YES ✓' if REPLICATE_API_TOKEN else 'NO ✗ — set REPLICATE_API_TOKEN in .env'}")
    print("  Running at: http://localhost:5000")
    print("=" * 55)
    app.run(debug=True, port=5000)