#!/usr/bin/env bash
set -euo pipefail

# debug_bib_runner.sh
# Splits references-fixed.bib into single-entry files, then appends them
# one-by-one into references-debug.bib and runs a full LaTeX build after
# each append. Stops on the first Biber WARN or ERROR and prints the log.

WORKDIR="$(pwd)"
SRC="references-fixed.bib"
DEBUG="references-debug.bib"
TMPDIR="$(mktemp -d)"

if [ ! -f "$SRC" ]; then
  echo "Source file $SRC not found" >&2
  exit 1
fi

rm -f "$DEBUG"

echo "Splitting $SRC into individual entries in $TMPDIR..."

awk -v outdir="$TMPDIR" '
  /^@/ { if (entry!="") { fname = sprintf("%s/entry_%03d.bib", outdir, ++n); print entry > fname; close(fname); entry=$0"\n"; } else { entry=$0"\n" } next }
  { entry = entry $0 "\n" }
  END { if (entry!="") { fname = sprintf("%s/entry_%03d.bib", outdir, ++n); print entry > fname; close(fname); } }
' "$SRC"

entries=("$TMPDIR"/entry_*.bib)
if [ ${#entries[@]} -eq 0 ]; then
  echo "No entries found in $SRC" >&2
  exit 1
fi

echo "Found ${#entries[@]} entries. Starting incremental build test..."

INDEX=0
for entry in "$TMPDIR"/entry_*.bib; do
  INDEX=$((INDEX+1))
  echo
  echo "=== Adding entry $INDEX: $(basename "$entry") ==="
  cat "$entry" >> "$DEBUG"

  echo "Running pdflatex (1)..."
  pdflatex -interaction=nonstopmode main.tex > /dev/null || true

  echo "Running biber..."
  biber main > biber.log 2>&1 || true

  # Detect only severe Biber problems: ERROR lines, BibTeX subsystem parse
  # errors, or duplicate-key warnings. Ignore ordinary "I didn't find a
  # database entry" warnings which are expected when the .bib doesn't yet
  # contain keys cited in the document.
  if grep -E "^ERROR -|BibTeX subsystem:|WARN - Duplicate entry key" biber.log >/dev/null 2>&1; then
    echo "Detected severe Biber WARN/ERROR after adding $(basename \"$entry\"):"
    sed -n '1,200p' biber.log
    echo "Problematic entry (appended to $DEBUG):"
    sed -n '1,200p' "$entry"
    echo "Stopped at entry $INDEX of ${#entries[@]}."
    exit 0
  fi

  echo "Running pdflatex (2)..."
  pdflatex -interaction=nonstopmode main.tex > /dev/null || true
  echo "Running pdflatex (3)..."
  pdflatex -interaction=nonstopmode main.tex > /dev/null || true

  echo "Entry $INDEX OK (no Biber WARN/ERROR). Continuing..."
done

echo
echo "All ${#entries[@]} entries added without Biber WARN/ERROR."
echo "Final debug file: $DEBUG"
exit 0
