# Creator Reel Pipeline

This folder contains a free fallback renderer for @aadityaxo.

## Flow

1. A valid public image URL plus hook/body/duration is written to creator/input.json.
2. GitHub Actions renders a 9:16 MP4 with subtle Ken Burns motion, readability panels, progress motion, and @aadityaxo branding.
3. creator/output/latest.mp4 is committed so the public raw GitHub URL can be used as a media source when appropriate.

This is a fallback for times when no free AI-video entitlement is available. It does not claim to create new AI motion; it turns a strong visual into a polished motion Reel.
