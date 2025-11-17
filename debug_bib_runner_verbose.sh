#!/usr/bin/env bash
# Robust verbose incremental bib test runner
WORKDIR="$(pwd)"
SRC="references-fixed.bib"
DEBUG="references-debug.bib"
TMPDIR="$(mktemp -d)"
LOG="debug_verbose.log"

echo "debug runner start" > "$LOG"

if [ ! -f "$SRC" ]; then
  echo "Source $SRC not found" | tee -a "$LOG"
  exit 1
fi

rm -f "$DEBUG"

awk -v outdir="$TMPDIR" '
  /^@/ { if (entry!="") { fname = sprintf("%s/entry_%03d.bib", outdir, ++n); print entry > fname; close(fname); entry=$0"\n"; } else { entry=$0"\n" } next }
  { entry = entry $0 "\n" }
  END { if (entry!="") { fname = sprintf("%s/entry_%03d.bib", outdir, ++n); print entry > fname; close(fname); } }
' "$SRC"

entries=("$TMPDIR"/entry_*.bib)
count=${#entries[@]}
echo "Found $count entries" | tee -a "$LOG"

idx=0
for entry in "$TMPDIR"/entry_*.bib; do
  idx=$((idx+1))
  echo "\n--- Appending entry $idx/$count: $(basename "$entry") ---" | tee -a "$LOG"
  cat "$entry" >> "$DEBUG"

  echo "pdflatex (1)" | tee -a "$LOG"
  pdflatex -interaction=nonstopmode main.tex >> "$LOG" 2>&1 || true

  echo "biber run" | tee -a "$LOG"
  biber main >> "$LOG" 2>&1 || true

  # Look for severe problems
  if grep -E "^ERROR -|BibTeX subsystem:|WARN - Duplicate entry key" "$LOG" >/dev/null; then
    echo "SEVERE BIBER PROBLEM after appending $(basename "$entry")" | tee -a "$LOG"
    echo "---- biber log tail ----" | tee -a "$LOG"
    sed -n '1,240p' main.blg | tee -a "$LOG"
    echo "---- problematic entry ----" | tee -a "$LOG"
    sed -n '1,240p' "$entry" | tee -a "$LOG"
    echo "Stopped at $idx/$count" | tee -a "$LOG"
    exit 2
  fi

  echo "pdflatex (2/3)" | tee -a "$LOG"
  pdflatex -interaction=nonstopmode main.tex >> "$LOG" 2>&1 || true
  pdflatex -interaction=nonstopmode main.tex >> "$LOG" 2>&1 || true

  echo "Entry $idx OK" | tee -a "$LOG"
done

echo "All $count entries appended without severe biber errors" | tee -a "$LOG"
echo "Final debug file: $DEBUG" | tee -a "$LOG"
exit 0
