# OpenClaw skill: property-pipeline

This skill lets an OpenClaw agent run the property analytics pipeline: poll for new bank downloads, run the import, prompt you to review, and finalize.

## Install into OpenClaw

Copy the skill into your OpenClaw workspace so the agent can load it:

```bash
# Create workspace skills dir if needed
mkdir -p ~/.openclaw/workspace/skills

# Copy from repo (run from repo root)
cp -r scripts/openclaw/property-pipeline ~/.openclaw/workspace/skills/
```

Or, if your OpenClaw workspace is this repo, the agent may discover `scripts/openclaw/property-pipeline/` when you add it to the workspace skills path.

Then ask OpenClaw to **refresh skills** or restart. You can say e.g.:

- "Check for new bank downloads and run the pipeline"
- "Import last month's statements"
- "I've finished reviewing OCT2025, finalize it"
- "Wipe the property database"

## Script used by the skill

- `scripts/check_bank_downloads.py` — lists months with bank files in `data/property/bank-download/`. Use `--run` to run the pipeline only for months that have all four files (pipeline waits for the full set). Use `--require-all` to list only complete months without running.
