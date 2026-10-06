#!/usr/bin/env python3
import argparse
import json
import math
import subprocess
import urllib.request
from pathlib import Path

W, H, FPS = 1080, 1920, 30

PALETTES = {
    1: ("0x06101c", "0x0b1d31", "0x2dd4ff"),
    2: ("0x05080e", "0x111827", "0x60a5fa"),
    3: ("0x0a0812", "0x172033", "0xa5b4fc"),
    4: ("0x07120f", "0x13251d", "0x67e8f9"),
    5: ("0x0b0b10", "0x1e293b", "0x93c5fd"),
    6: ("0x0a0a0a", "0x17202a", "0x38bdf8"),
}

def load(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    for k in ("hook", "body"):
        if not str(d.get(k, "")).strip():
            raise ValueError("Missing required field: " + k)
    d["duration"] = int(d.get("duration", 8))
    if not 5 <= d["duration"] <= 15:
        raise ValueError("duration must be 5-15 seconds")
    d["music"] = bool(d.get("music", True))
    d["variant"] = int(d.get("variant", 1))
    d["variant"] = min(6, max(1, d["variant"]))
    d["image_url"] = str(d.get("image_url", ""))
    return d

def fetch_image(url, out):
    req = urllib.request.Request(url, headers={"User-Agent": "Jojo-Reel-Renderer/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        Path(out).write_bytes(r.read())

def render(input_path, output):
    d = load(input_path)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    bg1, bg2, accent = PALETTES[d["variant"]]
    dur = d["duration"]

    local = None
    if d["image_url"] and not d["image_url"].startswith("generated://"):
        local = out.parent / ("source_" + out.stem + ".jpg")
        fetch_image(d["image_url"], local)

    if local:
        src = str(local)
        video = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},zoompan=z='min(zoom+0.0008,1.08)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={FPS*dur}:s={W}x{H}:fps={FPS},"
            f"eq=saturation=0.88:contrast=1.04:brightness=-0.02,"
            f"vignette=PI/5,"
            f"drawbox=x=44:y=150:w={W-88}:h={H-300}:color=black@0.10:t=4,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{d['hook'].replace(chr(39), chr(39)+chr(92)+chr(39))}':"
            f"fontcolor=white:fontsize=66:x=(w-text_w)/2:y=420,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{d['body'].replace(chr(39), chr(39)+chr(92)+chr(39))}':"
            f"fontcolor=0xdbeafe:fontsize=38:x=(w-text_w)/2:y=520"
            f"[v]"
        )
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", src,
            "-f", "lavfi", "-i",
            f"sine=frequency=220:sample_rate=44100:duration={dur}",
            "-filter_complex", video + ";[1:a]volume=0.12,afade=t=in:st=0:d=0.8,afade=t=out:st=" + str(max(1,dur-1.2)) + ":d=1.2[a]",
            "-map", "[v]", "-map", "[a]",
            "-t", str(dur), "-c:v", "libx264", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", "-b:v", "4M",
            "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "1",
            "-movflags", "+faststart", str(out)
        ]
    else:
        motion_x = f"180+140*sin(t/{1.8 + d['variant']*0.15})"
        motion_y = f"760+90*cos(t/{2.0 + d['variant']*0.18})"
        vf = (
            f"drawbox=x=0:y=0:w=iw:h=ih:color={bg1}:t=fill,"
            f"drawbox=x=70:y=260:w=940:h=1160:color={bg2}@0.78:t=fill,"
            f"drawbox=x='{motion_x}':y='{motion_y}':w=360:h=360:color={accent}@0.18:t=fill,"
            f"drawbox=x='720-90*sin(t/2.4)':y='980+55*sin(t/2.1)':w=250:h=250:color={accent}@0.10:t=fill,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{d['hook'].replace(chr(39), chr(39)+chr(92)+chr(39))}':"
            f"fontcolor=white:fontsize=68:x=(w-text_w)/2:y=430,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{d['body'].replace(chr(39), chr(39)+chr(92)+chr(39))}':"
            f"fontcolor=0xdbeafe:fontsize=38:x=(w-text_w)/2:y=530,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='aadityaxo • build in public':"
            f"fontcolor=white@0.65:fontsize=28:x=(w-text_w)/2:y=1660,"
            f"vignette=PI/6"
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={bg1}:s={W}x{H}:r={FPS}:d={dur}",
            "-f", "lavfi", "-i", f"sine=frequency={220 + d['variant']*7}:sample_rate=44100:duration={dur}",
            "-vf", vf,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-b:v", "4M", "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "1",
            "-movflags", "+faststart", str(out)
        ]

    subprocess.run(cmd, check=True)
    subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-show_entries", "stream=width,height,codec_name,codec_type",
        "-of", "default=noprint_wrappers=1",
        str(out)
    ], check=True)
    print("Rendered:", out)

def validate(path):
    d = load(path)
    print("Validated:", d["duration"], "seconds, 9:16 target, variant", d["variant"])
    print("Image source:", "remote" if d["image_url"] and not d["image_url"].startswith("generated://") else "procedural fallback")
    print("Music:", d["music"])

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate")
    g.add_argument("--render")
    p.add_argument("--output", default="creator/output/latest.mp4")
    a = p.parse_args()
    validate(a.validate) if a.validate else render(a.render, a.output)
