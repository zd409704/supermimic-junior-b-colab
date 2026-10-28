#!/usr/bin/env bash
# Deterministic P1 freeze manifest: sha256 of every file under code/, configs/, notebooks/ + the runbook.
set -euo pipefail
cd /srv/claude/research/supermimic-junior-b-colab
find code configs notebooks docs/COLAB_RUNBOOK.md -type f ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 | sort -z | xargs -0 sha256sum
