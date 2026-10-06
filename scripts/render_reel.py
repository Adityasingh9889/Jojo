#!/usr/bin/env python3
import argparse, json, subprocess, textwrap
from pathlib import Path

W, H, FPS = 1080, 1920, 30

def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("image_url","hook","body"):
        if not str(data.get(key,"")).strip():
            raise ValueError("Missing required field: "+key)
    duration = int(data.get("duration",8))
    if not 5 <= duration <= 15:
        raise ValueError("duration must be between 5 and 15 seconds")
    data["duration"]=duration
    data["music"]=bool(data.get("music",False))
    return data

def validate(path):
    d=load(path)
    print(f"Validated: {d['duration']} seconds 9:16")
    print("Source: self-contained motion scene" if str(d["image_url"]).startswith("generated://") else "Source: public image URL")
    print("Music:", "original ambient bed" if d["music"] else "off")

def render(input_path, output):
    data=load(input_path)
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    work=Path("/tmp/jojo-reel"); work.mkdir(parents=True,exist_ok=True)
    title=work/"title.txt"; body=work/"body.txt"
    title.write_text(textwrap.fill(str(data["hook"]).strip(),width=24),encoding="utf-8")
    body.write_text(textwrap.fill(str(data["body"]).strip(),width=32),encoding="utf-8")
    d=data["duration"]

    generated=str(data["image_url"]).startswith("generated://")
    if generated:
        src=["-f","lavfi","-i",f"color=c=0x050b14:s={W}x{H}:r={FPS}:d={d}"]
        vf=(
            "drawbox=x=0:y=0:w=1080:h=1920:color=black@0.08:t=fill,"
            "drawbox=x='80+24*sin(0.8*t)':y=260:w=150:h=430:color=0x0b2842@0.92:t=fill,"
            "drawbox=x='300+28*cos(0.65*t)':y=180:w=170:h=500:color=0x0d3150@0.88:t=fill,"
            "drawbox=x='580+20*sin(0.55*t)':y=310:w=140:h=370:color=0x0b2946@0.90:t=fill,"
            "drawbox=x='790+32*cos(0.7*t)':y=210:w=165:h=470:color=0x102f4c@0.90:t=fill,"
            "drawbox=x=0:y=700:w=1080:h=1220:color=0x03070d@0.99:t=fill,"
            "drawbox=x=155:y=860:w=770:h=550:color=0x081521@1:t=fill,"
            "drawbox=x=185:y=890:w=710:h=455:color=0x04111f@1:t=fill,"
            "drawbox=x='210+18*sin(1.1*t)':y=930:w=650:h=12:color=0x4ecbff@0.55:t=fill,"
            "drawbox=x='210+24*cos(0.8*t)':y=980:w=330:h=10:color=0x67d9ff@0.38:t=fill,"
            "drawbox=x='210+16*sin(0.9*t)':y=1020:w=440:h=10:color=0x74a7ff@0.32:t=fill,"
            "drawbox=x='210+20*cos(0.7*t)':y=1060:w=290:h=10:color=0x55e7c2@0.34:t=fill,"
            "drawbox=x='210+14*sin(0.6*t)':y=1100:w=500:h=10:color=0x6f8cff@0.28:t=fill,"
            "drawbox=x=120:y=1425:w=840:h=75:color=0x091018@1:t=fill,"
            "drawbox=x='55+36*sin(1.1*t)':y=420:w=8:h=210:color=0x63d8ff@0.65:t=fill,"
            "drawbox=x='950+24*cos(0.9*t)':y=300:w=6:h=250:color=0x6aa8ff@0.55:t=fill,"
            "drawbox=x=54:y=118:w=972:h=355:color=0x06101c@0.78:t=fill,"
            "drawbox=x=54:y=118:w=9:h=355:color=0x63d8ff@1:t=fill,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:textfile=/tmp/jojo-reel/title.txt:fontcolor=white:fontsize=70:line_spacing=12:x=96:y=170,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:textfile=/tmp/jojo-reel/body.txt:fontcolor=white:fontsize=38:line_spacing=12:x=96:y=360,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='@aadityaxo':fontcolor=white@0.78:fontsize=28:x=74:y=1818,"
            f"drawbox=x=74:y=1870:w='932*t/{d}':h=8:color=0x63d8ff@0.95:t=fill,"
            "format=yuv420p"
        )
    else:
        image=work/"input"
        subprocess.run(["curl","-L","--fail","--retry","3","--retry-all-errors","-A","Mozilla/5.0",data["image_url"],"-o",str(image)],check=True)
        if image.stat().st_size<1000: raise RuntimeError("Downloaded image is unexpectedly small")
        src=["-loop","1","-i",str(image)]
        frames=d*FPS
        vf=(f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"zoompan=z='min(zoom+0.00035,1.055)':d={frames}:s={W}x{H}:fps={FPS},"
            "drawbox=x=0:y=0:w=1080:h=1920:color=black@0.16:t=fill,"
            "drawbox=x=54:y=118:w=972:h=388:color=0x06101c@0.84:t=fill,"
            "drawbox=x=54:y=118:w=9:h=388:color=0x63d8ff@1:t=fill,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:textfile=/tmp/jojo-reel/title.txt:fontcolor=white:fontsize=70:x=96:y=170,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:textfile=/tmp/jojo-reel/body.txt:fontcolor=white:fontsize=38:x=96:y=380,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='@aadityaxo':fontcolor=white@0.80:fontsize=28:x=74:y=1820,format=yuv420p")

    cmd=["ffmpeg","-y"]+src+["-t",str(d)]
    if data["music"]:
        tone1=f"sine=frequency=220:sample_rate=44100:duration={d}"
        tone2=f"sine=frequency=277.18:sample_rate=44100:duration={d}"
        fade=max(0,d-1.2)
        graph=f"[1:a][2:a]amix=inputs=2:duration=longest:weights='1 0.6',volume=0.32,afade=t=in:st=0:d=0.8,afade=t=out:st={fade}:d=1.2[a]"
        cmd += ["-f","lavfi","-i",tone1,"-f","lavfi","-i",tone2,"-filter_complex",graph,"-map","0:v:0","-map","[a]","-vf",vf,"-r",str(FPS),"-c:v","libx264","-preset","veryfast","-profile:v","high","-pix_fmt","yuv420p","-b:v","3M","-c:a","aac","-b:a","96k","-ar","44100","-ac","1","-shortest","-movflags","+faststart",str(out)]
    else:
        cmd += ["-vf",vf,"-r",str(FPS),"-an","-c:v","libx264","-preset","veryfast","-profile:v","high","-pix_fmt","yuv420p","-b:v","3M","-movflags","+faststart",str(out)]
    subprocess.run(cmd,check=True)
    print("Rendered:",out)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True); g.add_argument("--validate"); g.add_argument("--render")
    p.add_argument("--output",default="creator/output/latest.mp4"); a=p.parse_args()
    validate(a.validate) if a.validate else render(a.render,a.output)
