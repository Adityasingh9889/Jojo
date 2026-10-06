#!/usr/bin/env python3
import argparse
import json
import subprocess
import textwrap
from pathlib import Path
from urllib.parse import urlparse

W, H, FPS = 1080, 1920, 30

def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    required = ["image_url", "hook", "body"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        raise ValueError("Missing required fields: " + ", ".join(missing))
    duration = int(data.get("duration", 15))
    if duration < 5 or duration > 15:
        raise ValueError("duration must be between 5 and 15 seconds")
    data["duration"] = duration
    data["music"] = bool(data.get("music", False))
    return data

def validate(path):
    data = load(path)
    print("Validated:", data["duration"], "seconds 9:16")
    print("Hook:", data["hook"])
    print("Image URL present: yes")
    print("Music:", "original ambient bed" if data["music"] else "off")

def render(input_path, output):
    data = load(input_path)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    work = Path("/tmp/jojo-reel")
    work.mkdir(parents=True, exist_ok=True)

    url_path = urlparse(data["image_url"]).path.lower()
    source = work / ("input.svg" if url_path.endswith(".svg") else "input.bin")
    image = work / "input.jpg"
    title_file = work / "title.txt"
    body_file = work / "body.txt"

    subprocess.run([
        "curl", "-L", "--fail", "--retry", "3", "--retry-all-errors",
        "-A", "Mozilla/5.0", data["image_url"], "-o", str(source)
    ], check=True)

    if source.stat().st_size < 1000:
        raise RuntimeError("Downloaded image is unexpectedly small")

    if url_path.endswith(".svg"):
        subprocess.run([
            "convert", str(source), "-background", "black",
            "-flatten", "-quality", "92", str(image)
        ], check=True)
    else:
        source.rename(image)

    hook = textwrap.fill(str(data["hook"]).strip(), width=25)
    body = textwrap.fill(str(data["body"]).strip(), width=34)
    title_file.write_text(hook, encoding="utf-8")
    body_file.write_text(body, encoding="utf-8")

    frames = data["duration"] * FPS
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        f"zoompan=z='min(zoom+0.00045,1.07)':"
        f"d={frames}:s={W}x{H}:fps={FPS},"
        "drawbox=x=0:y=0:w=1080:h=1920:color=black@0.20:t=fill,"
        "drawbox=x=54:y=118:w=972:h=420:color=0x07111e@0.90:t=fill,"
        "drawbox=x=54:y=118:w=10:h=420:color=0x63d8ff@1:t=fill,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "textfile=/tmp/jojo-reel/title.txt:"
        "fontcolor=white:fontsize=76:line_spacing=16:"
        "x=92:y=175:box=0,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "textfile=/tmp/jojo-reel/body.txt:"
        "fontcolor=white:fontsize=42:line_spacing=14:"
        "x=92:y=390:box=0,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "text='@aadityaxo':fontcolor=white@0.82:fontsize=30:"
        "x=72:y=1818,"
        "drawbox=x=72:y=1870:w='936*t/" + str(data["duration"]) + "':"
        "h=8:color=0x63d8ff@0.95:t=fill,"
        "format=yuv420p"
    )

    base = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image),
        "-t", str(data["duration"]),
    ]

    if data["music"]:
        d = str(data["duration"])
        pad_expr = (
            "0.050*sin(2*PI*220*t)+"
            "0.032*sin(2*PI*261.63*t)+"
            "0.024*sin(2*PI*329.63*t)+"
            "0.018*sin(2*PI*392*t)"
        )
        kick_expr = "0.075*sin(2*PI*64*t)*exp(-38*mod(t,0.5))"
        audio = f"aevalsrc=exprs='{pad_expr}':s=44100:d={d},tremolo=f=0.18:d=0.55,volume=0.8"
        kick = f"aevalsrc=exprs='{kick_expr}':s=44100:d={d},volume=0.65"
        air = f"anoisesrc=color=pink:amplitude=0.035:sample_rate=44100:duration={d},highpass=f=2500,lowpass=f=9000,volume=0.16"
        fade_out_start = max(0, data["duration"] - 1.2)
        agraph = (
            f"[1:a]afade=t=in:st=0:d=0.8,afade=t=out:st={fade_out_start}:d=1.2[a1];"
            "[2:a][3:a]amix=inputs=2:duration=longest,volume=0.70[a2];"
            "[a1][a2]amix=inputs=2:duration=longest,volume=0.82[a]"
        )
        cmd = base + [
            "-f", "lavfi", "-i", audio,
            "-f", "lavfi", "-i", kick,
            "-f", "lavfi", "-i", air,
            "-filter_complex", agraph,
            "-map", "0:v:0", "-map", "[a]",
            "-vf", vf,
            "-r", str(FPS),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
            "-b:v", "3M",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-ac", "2",
            "-shortest",
            "-movflags", "+faststart",
            str(out),
        ]
    else:
        cmd = base + [
            "-vf", vf,
            "-r", str(FPS),
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
            "-b:v", "3M",
            "-movflags", "+faststart",
            str(out),
        ]

    subprocess.run(cmd, check=True)
    print("Rendered:", out)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate", metavar="JSON")
    g.add_argument("--render", metavar="JSON")
    p.add_argument("--output", default="creator/output/latest.mp4")
    args = p.parse_args()
    if args.validate:
        validate(args.validate)
    else:
        render(args.render, args.output)
