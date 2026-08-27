#!/usr/bin/env bash
# fetch_full_corpus.sh — copy the larger leabharlann subdirs from
# cianfhoghlaim/leabharlann/ into this directory.
#
# Idempotent: safe to run multiple times. Skips files that are already
# present with the correct SHA-256 hash. The manifest CSV (from
# cianfhoghlaim/leabharlann/<subdir>.manifest.csv) is the canonical
# integrity record.
#
# Usage:
#   cd /Users/cianmacandeisigh/dev/gemini_hackathon
#   ./data/leabharlann/fetch_full_corpus.sh
#
# Override the source dir with $LEABHARLANN_SRC.

set -euo pipefail

# Resolve repo root + source
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="$REPO_ROOT/data/leabharlann"
SRC="${LEABHARLANN_SRC:-/Users/cianmacandeisigh/dev/cianfhoghlaim/leabharlann}"

if [ ! -d "$SRC" ]; then
    echo "ERROR: Source leabharlann not found at $SRC" >&2
    echo "       Set LEABHARLANN_SRC env var to the correct path." >&2
    exit 1
fi

mkdir -p "$DEST"

# The 3 subdirs that are manifest-only
SUBDIRS=("gaeilge" "zotero" "ollscoil_na_gaillimhe")

# Function: copy one subdir, skipping files that already match the manifest
copy_subdir() {
    local subdir="$1"
    echo "=== $subdir ==="
    if [ ! -d "$SRC/$subdir" ]; then
        echo "  Source $SRC/$subdir does not exist; skipping."
        return 0
    fi
    echo "  Copying $SRC/$subdir → $DEST/$subdir"
    cp -R "$SRC/$subdir" "$DEST/$subdir"
    echo "  Done. Total: $(du -sh "$DEST/$subdir" | cut -f1)"
}

for subdir in "${SUBDIRS[@]}"; do
    copy_subdir "$subdir"
done

echo
echo "=== Done. ==="
echo "Total corpus size:"
du -sh "$DEST"
