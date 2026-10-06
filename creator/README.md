# Creator Reel + Verified Instagram QA Pipeline

This folder contains the free fallback renderer plus a closed-loop Instagram QA runner.

## Verified loop

1. Build candidate.
2. Publish candidate to Instagram.
3. Retrieve the published Instagram media.
4. Download representative frames from the actual published asset.
5. Run visual QA.
6. If the score is below 9.2/10 or a critical defect is found, delete the rejected media.
7. Change the defective variant, rebuild, and publish again.
8. Repeat for at most 6 iterations.
9. Stop only when a verified winner clears the threshold.
10. Persist the QA result and winning recipe for reuse.

The workflow fails closed: missing credentials, missing published media, or failed visual verification prevents the system from calling the asset approved.

## GitHub setup

Add these repository secrets:

- `IG_USER_ID` — your Instagram professional account ID. The connected account currently resolves to `17841436826886907`.
- `META_ACCESS_TOKEN` — a Meta/Instagram access token with the permissions required for publishing and deleting media.
- `OPENAI_API_KEY` — used only for the visual QA reviewer.

Optional repository variables:

- `META_GRAPH_VERSION` — Graph API version validated for your account.
- `OPENAI_QA_MODEL` — an enabled model that accepts image inputs.

No media-source variable is needed. The workflow commits each unique candidate and uses its public raw GitHub URL before asking Instagram to fetch it.

## Files

- `scripts/render_reel.py` — 9:16 renderer with six controlled visual variants.
- `scripts/instagram_quality_loop_v2.py` — publish -> retrieve -> inspect -> delete -> rebuild loop.
- `.github/workflows/instagram-quality-loop.yml` — manual-only runner.
- `creator/publish.json` — current story configuration.
- `creator/qa_profile.json` — persistent quality rules and approved recipe memory.

## Important limitation

The free renderer is a controlled procedural fallback. It is not a replacement for a photorealistic AI-video generator. The loop is designed so a stronger generated/uploaded asset can later be plugged into the same publish -> verify -> delete/rebuild pipeline without changing the QA philosophy.

Native Instagram song attachment is not faked. Use exact native audio only when the publishing integration can safely resolve it; otherwise use allowed embedded audio.
