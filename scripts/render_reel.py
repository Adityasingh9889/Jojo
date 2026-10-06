#!/usr/bin/env python3
import argparse,json,subprocess
from pathlib import Path

W,H,FPS=1080,1920,30

def load(path):
    d=json.loads(Path(path).read_text(encoding="utf-8"))
    for k in ("image_url","hook","body"):
        if not str(d.get(k,"")).strip(): raise ValueError("Missing required field: "+k)
    d["duration"]=int(d.get("duration",8))
    if not 5<=d["duration"]<=15: raise ValueError("duration must be 5-15 seconds")
    d["music"]=bool(d.get("music",False))
    return d

def validate(path):
    d=load(path)
    print("Validated:",d["duration"],"seconds 9:16")
    print("Source: self-contained motion scene" if str(d["image_url"]).startswith("generated://") else "Source: public image URL")
    print("Music:",d["music"])

def render(input_path,output):
    d=load(input_path); out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    dur=str(d["duration"])
    # Deterministic, dependency-free 9:16 background + original ambient two-note bed.
    if str(d["image_url"]).startswith("generated://"):
        cmd=[
            "ffmpeg","-y",
            "-f","lavfi","-i",f"color=c=0x06101c:s={W}x{H}:r={FPS}:d={dur}",
            "-f","lavfi","-i",f"sine=frequency=220:sample_rate=44100:duration={dur}",
            "-f","lavfi","-i",f"sine=frequency=277.18:sample_rate=44100:duration={dur}",
            "-filter_complex","[1:a][2:a]amix=inputs=2:duration=longest:weights='1 0.6',volume=0.20,afade=t=in:st=0:d=0.8,afade=t=out:st=6.8:d=1.2[a]",
            "-map","0:v:0","-map","[a]",
            "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-b:v","2M",
            "-c:a","aac","-b:a","96k","-ar","44100","-ac","1","-shortest",
            "-movflags","+faststart",str(out)
        ]
    else:
        raise ValueError("Only generated:// source is enabled in this verified fallback")
    subprocess.run(cmd,check=True)
    subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-show_entries","stream=width,height,codec_name","-of","default=noprint_wrappers=1",str(out)],check=True)
    print("Rendered:",out)

if __name__=="__main__":
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate"); g.add_argument("--render"); p.add_argument("--output",default="creator/output/latest.mp4")
    a=p.parse_args()
    validate(a.validate) if a.validate else render(a.render,a.output)
