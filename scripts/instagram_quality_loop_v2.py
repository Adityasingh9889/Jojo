#!/usr/bin/env python3
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GRAPH = os.environ.get("META_GRAPH_BASE", "https://graph.facebook.com")
GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v23.0")
MAX_ITER = min(int(os.environ.get("QA_MAX_ITERATIONS", "6")), 6)
THRESHOLD = float(os.environ.get("QA_MIN_SCORE", "9.2"))

IG_USER_ID = os.environ.get("IG_USER_ID", "")
META_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_QA_MODEL", "gpt-4.1-mini")
PUBLISH_SOURCE_TEMPLATE = os.environ.get("PUBLISH_SOURCE_TEMPLATE", "")

def fail(msg):
    print("ERROR:", msg, file=sys.stderr)
    raise SystemExit(1)

def meta_request(method, path, params=None, body=None):
    url = f"{GRAPH}/{GRAPH_VERSION}/{path.lstrip('/')}"
    params = dict(params or {})
    body = dict(body or {})
    headers = {"User-Agent": "Jojo-Instagram-Verified-QA/1.0"}
    if method == "GET":
        params["access_token"] = META_TOKEN
        url += "?" + urllib.parse.urlencode(params)
        data = None
    else:
        body["access_token"] = META_TOKEN
        data = urllib.parse.urlencode(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        fail(f"Meta API {e.code}: {e.read().decode(errors='replace')[:1600]}")

def require_env():
    missing = [k for k, v in {
        "IG_USER_ID": IG_USER_ID,
        "META_ACCESS_TOKEN": META_TOKEN,
        "OPENAI_API_KEY": OPENAI_KEY,
        "PUBLISH_SOURCE_TEMPLATE": PUBLISH_SOURCE_TEMPLATE
    }.items() if not v]
    if missing:
        fail("Missing required GitHub secrets/variables: " + ", ".join(missing))

def load_cfg(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    cfg.setdefault("kind", "story")
    cfg.setdefault("hook", "")
    cfg.setdefault("body", "")
    cfg.setdefault("caption", "")
    cfg.setdefault("duration", 8)
    cfg.setdefault("variant_sequence", [1, 2, 3, 4, 5, 6])
    if cfg["kind"] not in ("story", "reel"):
        fail("kind must be story or reel")
    return cfg

def ffprobe(path):
    raw = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-show_entries", "stream=index,codec_type,codec_name,width,height,sample_rate,channels",
        "-of", "json", str(path)
    ], text=True)
    return json.loads(raw)

def extract_frames(media_path, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    meta = ffprobe(media_path)
    duration = float(meta.get("format", {}).get("duration") or 0)
    video = next((s for s in meta.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video:
        fail("No video stream found")
    w, h = int(video.get("width", 0)), int(video.get("height", 0))
    ratio = w / h if h else 0
    if not (w and h) or abs(ratio - 9/16) > 0.08:
        fail(f"Not a valid 9:16 candidate: {w}x{h}")
    times = [0.15, max(0.30, duration * 0.33), max(0.60, duration * 0.66), max(0.80, duration - 0.20)]
    frames = []
    for i, t in enumerate(times):
        p = outdir / f"frame_{i}.jpg"
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(t), "-i", str(media_path),
            "-frames:v", "1", "-q:v", "3", str(p)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        frames.append(p)
    return frames

def to_data_url(path):
    encoded = base64.b64encode(Path(path).read_bytes()).decode()
    return "data:image/jpeg;base64," + encoded

def openai_review(frames, cfg, iteration):
    prompt = f"""You are the final visual QA reviewer for an Instagram creator.
Review the supplied representative frames from the ACTUAL published Instagram asset.
Iteration {iteration}/{MAX_ITER}. Minimum publish score: {THRESHOLD}/10.
Desired style: premium, dark/navy tech aesthetic, restrained blue/cyan, photographic materials,
physically believable motion, strong hierarchy, mobile-safe framing.

Score 0-10:
realism, composition, lighting, material_realism, motion_read, text_readability,
mobile_safe_framing, technical_polish, audio_expectation.

Return strict JSON only:
{{
  "overall_score": 0,
  "publish_ok": false,
  "critical_defects": [],
  "fixes": [],
  "next_variant": 1,
  "scores": {{
    "realism": 0, "composition": 0, "lighting": 0, "material_realism": 0,
    "motion_read": 0, "text_readability": 0, "mobile_safe_framing": 0,
    "technical_polish": 0, "audio_expectation": 0
  }}
}}

Reject obvious AI/render artifacts, warped or duplicated objects, impossible reflections,
tiny/unreadable text, bad crops, broken screens, fake-looking materials, or unfinished composition.
Candidate hook: {cfg.get("hook","")}
Candidate body: {cfg.get("body","")}
"""
    payload = {
        "model": OPENAI_MODEL,
        "input": [{
            "role": "user",
            "content": [{"type": "input_text", "text": prompt}] +
                      [{"type": "input_image", "image_url": to_data_url(f)} for f in frames]
        }]
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + OPENAI_KEY,
            "User-Agent": "Jojo-Instagram-Verified-QA/1.0"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            obj = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        fail("OpenAI QA API error: " + e.read().decode(errors="replace")[:1600])
    text_out = obj.get("output_text", "")
    if not text_out:
        bits = []
        for item in obj.get("output", []):
            for c in item.get("content", []):
                if c.get("type") in ("output_text", "text") and c.get("text"):
                    bits.append(c["text"])
        text_out = "".join(bits)
    start, end = text_out.find("{"), text_out.rfind("}")
    if start < 0 or end <= start:
        fail("OpenAI QA returned no JSON")
    try:
        return json.loads(text_out[start:end+1])
    except Exception as e:
        fail("Could not parse QA JSON: " + str(e))

def publish_video(cfg, iteration):
    media_type = "STORIES" if cfg["kind"] == "story" else "REELS"
    url = PUBLISH_SOURCE_TEMPLATE.format(iteration=iteration)
    body = {"media_type": media_type, "video_url": url}
    if cfg.get("caption") and cfg["kind"] == "reel":
        body["caption"] = cfg["caption"]
    creation = meta_request("POST", f"{IG_USER_ID}/media", body=body)
    cid = creation.get("id")
    if not cid:
        fail("Meta container creation returned no id")
    for _ in range(30):
        status = meta_request("GET", cid, params={"fields": "id,status_code,status"})
        code = status.get("status_code")
        if code in ("FINISHED", "PUBLISHED"):
            break
        if code in ("ERROR", "EXPIRED"):
            fail("Meta container failed: " + json.dumps(status))
        time.sleep(10)
    published = meta_request("POST", f"{IG_USER_ID}/media_publish", body={"creation_id": cid})
    mid = published.get("id")
    if not mid:
        fail("Meta publish returned no media id")
    return mid

def get_published(mid):
    return meta_request(
        "GET", mid,
        params={"fields": "id,media_type,media_url,permalink,timestamp,caption"}
    )

def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Jojo-Instagram-Verified-QA/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        Path(path).write_bytes(r.read())

def delete_published(mid):
    return meta_request("DELETE", mid)

def commit_candidate(candidate, cfg_path, iter_path):
    subprocess.run(["git", "config", "user.name", "Jojo QA Bot"], check=True)
    subprocess.run([
        "git", "config", "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com"
    ], check=True)
    subprocess.run(["git", "add", str(candidate), str(iter_path)], check=True)
    subprocess.run(["git", "commit", "-m", f"🧪 publish QA candidate {candidate.stem}"], check=True)
    subprocess.run(["git", "push"], check=True)
    time.sleep(5)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--candidate-dir", default="creator/qa_runs")
    args = parser.parse_args()

    require_env()
    cfg = load_cfg(args.config)
    root = Path(args.candidate_dir)
    root.mkdir(parents=True, exist_ok=True)
    results = []
    working = dict(cfg)

    for iteration in range(1, MAX_ITER + 1):
        seq = working.get("variant_sequence") or [1, 2, 3, 4, 5, 6]
        variant = int(working.get("variant") or seq[min(iteration - 1, len(seq) - 1)])
        working["variant"] = variant
        iter_cfg = root / f"iteration_{iteration}.json"
        iter_cfg.write_text(json.dumps(working, indent=2), encoding="utf-8")

        candidate = root / f"candidate_{iteration}.mp4"
        subprocess.run([
            sys.executable, "scripts/render_reel.py",
            "--render", str(iter_cfg),
            "--output", str(candidate)
        ], check=True)
        extract_frames(candidate, root / f"frames_{iteration}")

        commit_candidate(candidate, args.config, iter_cfg)

        media_id = publish_video(working, iteration)
        print("Published:", media_id)

        published = get_published(media_id)
        media_url = published.get("media_url")
        if not media_url:
            delete_published(media_id)
            fail("Published media could not be retrieved for actual verification; deleted it.")

        downloaded = root / f"published_{iteration}.mp4"
        download(media_url, downloaded)
        published_frames = extract_frames(downloaded, root / f"published_frames_{iteration}")

        review = openai_review(published_frames, working, iteration)
        score = float(review.get("overall_score", 0))
        passed = bool(review.get("publish_ok")) and score >= THRESHOLD

        results.append({
            "iteration": iteration,
            "media_id": media_id,
            "score": score,
            "review": review,
            "published": published
        })

        print(json.dumps(results[-1], indent=2))

        if passed:
            Path(root / "WINNER.json").write_text(
                json.dumps(results[-1], indent=2), encoding="utf-8"
            )
            print(f"WINNER iteration={iteration} score={score}")
            return

        delete_published(media_id)
        print("Deleted rejected media:", media_id)

        working["variant"] = int(review.get("next_variant") or ((variant % 6) + 1))
        working["defects"] = review.get("critical_defects", [])
        working["fixes"] = review.get("fixes", [])

    Path(root / "FAILURE.json").write_text(
        json.dumps({"results": results}, indent=2), encoding="utf-8"
    )
    fail(f"No candidate reached {THRESHOLD}/10 after {MAX_ITER} iterations.")

if __name__ == "__main__":
    main()
