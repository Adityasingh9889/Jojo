#!/usr/bin/env python3
import argparse, base64, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.parse import urlparse
import urllib.request
import urllib.error

GRAPH = os.environ.get("META_GRAPH_BASE", "https://graph.facebook.com")
GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v23.0")
MAX_ITER = min(int(os.environ.get("QA_MAX_ITERATIONS", "6")), 6)
THRESHOLD = float(os.environ.get("QA_MIN_SCORE", "9.2"))
IG_USER_ID = os.environ.get("IG_USER_ID", "")
META_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_QA_MODEL", "gpt-4.1-mini")

def fail(msg):
    print("ERROR:", msg, file=sys.stderr)
    raise SystemExit(1)

def api(method, path, params=None, body=None):
    url = f"{GRAPH}/{GRAPH_VERSION}/{path.lstrip('/')}"
    headers = {"User-Agent": "Jojo-Instagram-QA/1.0"}
    data = None
    if method == "GET":
        q = dict(params or {})
        q["access_token"] = META_TOKEN
        from urllib.parse import urlencode
        url += "?" + urlencode(q)
    else:
        payload = dict(body or {})
        payload["access_token"] = META_TOKEN
        data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        fail(f"Meta API {e.code}: {raw[:1200]}")

def require_secrets():
    missing = [k for k, v in {
        "IG_USER_ID": IG_USER_ID,
        "META_ACCESS_TOKEN": META_TOKEN,
        "OPENAI_API_KEY": OPENAI_KEY,
    }.items() if not v]
    if missing:
        fail("Missing required GitHub Actions secrets: " + ", ".join(missing))

def load_cfg(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    cfg.setdefault("kind", "story")
    cfg.setdefault("hook", "")
    cfg.setdefault("body", "")
    cfg.setdefault("caption", "")
    cfg.setdefault("duration", 8)
    cfg.setdefault("variant_sequence", [1,2,3,4,5,6])
    if cfg["kind"] not in ("story", "reel", "image_post"):
        fail("kind must be story, reel or image_post")
    return cfg

def ffprobe(path):
    cmd=["ffprobe","-v","error","-show_entries","format=duration:stream=index,codec_type,codec_name,width,height,sample_rate,channels",
         "-of","json",str(path)]
    out=subprocess.check_output(cmd,text=True)
    return json.loads(out)

def extract_frames(media_path, outdir, count=4):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    meta=ffprobe(media_path)
    duration=float(meta.get("format",{}).get("duration") or 0)
    streams=meta.get("streams",[])
    video=next((s for s in streams if s.get("codec_type")=="video"),None)
    if not video: fail("Candidate has no video stream")
    w,h=int(video.get("width",0)),int(video.get("height",0))
    if h == 0 or w == 0 or abs((w/h) - (9/16)) > 0.08:
        fail(f"Candidate is not a convincing 9:16 asset: {w}x{h}")
    times=[0.15, max(0.3,duration*0.33), max(0.6,duration*0.66), max(0.8,duration-0.2)]
    frames=[]
    for i,t in enumerate(times[:count]):
        p=outdir/f"frame_{i}.jpg"
        subprocess.run(["ffmpeg","-y","-ss",str(t),"-i",str(media_path),"-frames:v","1","-q:v","3",str(p)],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        frames.append(p)
    return frames

def data_url(path):
    b=base64.b64encode(Path(path).read_bytes()).decode()
    return "data:image/jpeg;base64,"+b

def openai_review(frames, cfg, iteration):
    if not OPENAI_KEY:
        fail("OPENAI_API_KEY is required for visual QA")
    prompt = f"""
You are the final visual QA reviewer for an Instagram creator pipeline.
Review the supplied representative frames from the ACTUAL published Instagram asset.
This is iteration {iteration} of at most {MAX_ITER}. Brand: premium dark/navy/cyan tech aesthetic, physically plausible, photographic materials, mobile-safe 9:16.

Score 0-10 for:
realism, composition, lighting, material_realism, motion_read, text_readability, mobile_safe_framing, technical_polish, audio_expectation.
Return strict JSON only:
{{
  "overall_score": number,
  "publish_ok": boolean,
  "critical_defects": ["..."],
  "fixes": ["..."],
  "scores": {{
    "realism": number, "composition": number, "lighting": number,
    "material_realism": number, "motion_read": number,
    "text_readability": number, "mobile_safe_framing": number,
    "technical_polish": number, "audio_expectation": number
  }},
  "next_variant": integer 1-6
}}
Reject warped/unphysical objects, duplicated objects, broken screens, impossible reflections,
bad crops, tiny text, generic CGI look, obvious rendering artifacts, or anything that feels unfinished.
A score >= {THRESHOLD} is required.
Candidate hook: {cfg.get("hook","")}
Candidate body: {cfg.get("body","")}
"""
    payload={
      "model":OPENAI_MODEL,
      "input":[{
        "role":"user",
        "content":[{"type":"input_text","text":prompt}]+[
            {"type":"input_image","image_url":data_url(f)} for f in frames
        ]
      }]
    }
    req=urllib.request.Request(
      "https://api.openai.com/v1/responses",
      data=json.dumps(payload).encode(),
      headers={"Content-Type":"application/json","Authorization":"Bearer "+OPENAI_KEY,
               "User-Agent":"Jojo-Instagram-QA/1.0"},
      method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            obj=json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        fail("OpenAI QA API error: "+e.read().decode(errors="replace")[:1500])
    text_out=obj.get("output_text","").strip()
    if not text_out:
        # compatible fallback for response blocks
        bits=[]
        for item in obj.get("output",[]):
            for c in item.get("content",[]):
                if c.get("type") in ("output_text","text") and c.get("text"):
                    bits.append(c["text"])
        text_out="".join(bits).strip()
    start=text_out.find("{")
    end=text_out.rfind("}")
    if start<0 or end<=start:
        fail("OpenAI QA returned no parseable JSON")
    try:
        return json.loads(text_out[start:end+1])
    except Exception as e:
        fail("OpenAI QA JSON parse failed: "+str(e))

def publish_video(path, cfg):
    remote = os.environ.get("PUBLISH_SOURCE_URL","").strip()
    # Use configured public URL when supplied; otherwise the repo workflow supplies the raw URL.
    video_url = remote
    if not video_url:
        fail("PUBLISH_SOURCE_URL must point to the public candidate media URL for the Meta API")
    media_type = "STORIES" if cfg["kind"]=="story" else "REELS"
    body={"media_type":media_type,"video_url":video_url}
    if cfg.get("caption") and cfg["kind"]!="story":
        body["caption"]=cfg["caption"]
    creation=api("POST", f"{IG_USER_ID}/media", body=body)
    cid=creation.get("id")
    if not cid: fail("Meta media container creation returned no id")
    for _ in range(30):
        st=api("GET", cid, params={"fields":"id,status_code,status"})
        code=st.get("status_code")
        if code in ("FINISHED","PUBLISHED"): break
        if code in ("ERROR","EXPIRED"): fail("Meta media container failed: "+json.dumps(st))
        time.sleep(10)
    published=api("POST", f"{IG_USER_ID}/media_publish", body={"creation_id":cid})
    mid=published.get("id")
    if not mid: fail("Meta publish returned no media id")
    return mid

def fetch_published(mid):
    return api("GET", mid, params={"fields":"id,media_type,media_url,permalink,timestamp,caption"})

def download(url, path):
    req=urllib.request.Request(url,headers={"User-Agent":"Jojo-Instagram-QA/1.0"})
    with urllib.request.urlopen(req,timeout=60) as r:
        Path(path).write_bytes(r.read())

def delete_media(mid):
    return api("DELETE", mid)

def regenerate(cfg, variant):
    cfg["variant"]=int(variant)
    return cfg

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",required=True)
    ap.add_argument("--candidate-dir",default="creator/qa_runs")
    args=ap.parse_args()
    require_secrets()
    cfg=load_cfg(args.config)
    root=Path(args.candidate_dir); root.mkdir(parents=True,exist_ok=True)
    results=[]
    working=dict(cfg)

    for iteration in range(1,MAX_ITER+1):
        variant_seq=working.get("variant_sequence") or [1,2,3,4,5,6]
        variant=working.get("variant") or variant_seq[min(iteration-1,len(variant_seq)-1)]
        working=regenerate(working,variant)
        working_path=root/f"iteration_{iteration}.json"
        working_path.write_text(json.dumps(working,indent=2),encoding="utf-8")

        candidate=root/f"candidate_{iteration}.mp4"
        cmd=[sys.executable,"scripts/render_reel.py","--render",str(working_path),"--output",str(candidate)]
        subprocess.run(cmd,check=True)

        frames=extract_frames(candidate, root/f"frames_{iteration}")
        # The public source URL is supplied by the workflow from the committed candidate.
        media_id=publish_video(candidate,working)
        print("Published candidate media id:",media_id)

        pub=fetch_published(media_id)
        pub_url=pub.get("media_url")
        downloaded=root/f"published_{iteration}.mp4"
        if pub_url:
            download(pub_url,downloaded)
            inspect_frames=extract_frames(downloaded, root/f"published_frames_{iteration}")
        else:
            inspect_frames=frames

        review=openai_review(inspect_frames,working,iteration)
        score=float(review.get("overall_score",0))
        ok=bool(review.get("publish_ok")) and score>=THRESHOLD
        results.append({"iteration":iteration,"media_id":media_id,"score":score,"review":review,"published":pub})

        if ok:
            Path(root/"WINNER.json").write_text(json.dumps(results[-1],indent=2),encoding="utf-8")
            print(json.dumps({"winner":True,"iteration":iteration,"media_id":media_id,"score":score},indent=2))
            return

        print("Rejected candidate:",json.dumps(review,indent=2))
        delete_media(media_id)
        print("Deleted rejected media:",media_id)
        next_variant=int(review.get("next_variant") or ((variant % 6)+1))
        working["variant"]=next_variant
        working["defects"]=review.get("critical_defects",[])
        working["fixes"]=review.get("fixes",[])

    Path(root/"FAILURE.json").write_text(json.dumps({"results":results},indent=2),encoding="utf-8")
    fail(f"No candidate reached {THRESHOLD}/10 within {MAX_ITER} iterations; nothing left published.")

if __name__=="__main__":
    main()
