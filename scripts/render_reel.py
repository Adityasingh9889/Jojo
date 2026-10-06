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

def make_generated_scene(path):
    """Create a self-contained 9:16 tech/night background without external assets."""
    w, h = 540, 960
    with open(path, "wb") as f:
        f.write(f"P6\n{w} {h}\n255\n".encode("ascii"))
        for y in range(h):
            for x in range(w):
                t = y / (h - 1)
                r = int(4 + 4 * t)
                g = int(10 + 12 * t)
                b = int(20 + 28 * t)
                # soft blue/cyan glow behind the window
                dx = (x - 385) / 220
                dy = (y - 355) / 260
                glow = max(0.0, 1.0 - (dx * dx + dy * dy))
                r += int(3 * glow)
                g += int(22 * glow)
                b += int(34 * glow)
                # skyline blocks
                if 90 < x < 180 and 265 < y < 615:
                    r, g, b = 11, 28, 46
                if 200 < x < 300 and 205 < y < 610:
                    r, g, b = 13, 34, 54
                if 320 < x < 418 and 155 < y < 620:
                    r, g, b = 12, 31, 52
                if 435 < x < 505 and 245 < y < 620:
                    r, g, b = 10, 26, 43
                # desk
                if y > 610:
                    r, g, b = 4, 7, 12
                # laptop body/screen
                if 115 < y < 660 and 80 < x < 455:
                    if 95 < y < 575 and 120 < x < 430:
                        r, g, b = 5, 16, 27
                    else:
                        r, g, b = 8, 13, 20
                # screen glow
                if 135 < y < 560 and 145 < x < 405:
                    r, g, b = 5, 19, 32
                f.write(bytes((max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b)))))

def prepare_image(data, work):
    image = work / "input.ppm"
    if str(data["image_url"]).startswith("generated://"):
        make_generated_scene(image)
    else:
        url_path = urlparse(data["image_url"]).path.lower()
        source = work / ("input.svg" if url_path.endswith(".svg") else "input.bin")
        subprocess.run([
            "curl", "-L", "--fail", "--retry", "3", "--retry-all-errors",
            "-A", "Mozilla/5.0", data["image_url"], "-o", str(source)
        ], check=True)
        if source.stat().st_size < 1000:
            raise RuntimeError("Downloaded image is unexpectedly small")
        # Use ffmpeg itself to decode common images/SVG is intentionally unsupported.
        # Convert non-PPM image sources by letting ffmpeg decode them directly later.
        image = source
    return image

def validate(path):
    data = load(path)
    source = "generated scene" if str(data["image_url"]).startswith("generated://") else "public image URL"
    print("Validated:", data["duration"], "seconds 9:16")
    print("Hook:", data["hook"])
    print("Source:", source)
    print("Music:", "original ambient bed" if data["music"] else "off")

def render(input_path, output):
    data = load(input_path)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    work = Path("/tmp/jojo-reel")
    work.mkdir(parents=True, exist_ok=True)
    image = prepare_image(data, work)
    title_file = work / "title.txt"
    body_file = work / "body.txt"

    hook = textwrap.fill(str(data["hook"]).strip(), width=25)
    body = textwrap.fill(str(data["body"]).strip(), width=34)
    title_file.write_text(hook, encoding="utf-8")
    body_file.write_text(body, encoding="utf-8")

    # Keep composition mobile-safe and use a gentle camera push.
    frames = data["duration"] * FPS
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        f"zoompan=z='min(zoom+0.00035,1.055)':"
        f"d={frames}:s={W}x{H}:fps={FPS},"
        "drawbox=x=0:y=0:w=1080:h=1920:color=black@0.16:t=fill,"
        "drawbox=x=58:y=120:w=964:h=388:color=0x06101c@0.84:t=fill,"
        "drawbox=x=58:y=120:w=9:h=388:color=0x63d8ff@1:t=fill,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "textfile=/tmp/jojo-reel/title.txt:"
        "fontcolor=white:fontsize=70:line_spacing=12:"
        "x=96:y=170:box=0,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "textfile=/tmp/jojo-reel/body.txt:"
        "fontcolor=white:fontsize=38:line_spacing=12:"
        "x=96:y=380:box=0,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "text='@aadityaxo':fontcolor=white@0.80:fontsize=28:"
        "x=74:y=1820,"
        "drawbox=x=74:y=1870:w='932*t/" + str(data["duration"]) + "':"
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
