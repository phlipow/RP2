#!/bin/bash
# Complete LaTeX build script for main.tex

set -e  # Exit on any error

cd "$(dirname "$0")" || exit 1

echo "========================================"
echo "LaTeX Document Build Process"
echo "========================================"
echo ""

echo "[1/5] Cleaning previous build files..."
rm -f main.aux main.bbl main.bcf main.blg main.log main.out main.pdf main.run.xml

echo "[2/5] First pdflatex pass..."
pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1

echo "[3/5] Running biber for bibliography..."
biber main > /dev/null 2>&1

echo "[4/5] Second pdflatex pass..."
pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1

echo "[5/5] Third pdflatex pass (final)..."
pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1

echo ""
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo ""

if [ -f main.pdf ]; then
    SIZE=$(stat -c%s main.pdf)
    PAGES=$(pdfinfo main.pdf 2>/dev/null | grep "Pages:" | awk '{print $2}')
    echo "✓ PDF created: main.pdf"
    echo "  Size: $SIZE bytes"
    echo "  Pages: $PAGES"
    echo ""
    echo "Build successful!"
else
    echo "✗ Error: main.pdf was not created"
    echo ""
    echo "Checking for errors in main.log:"
    tail -30 main.log
    exit 1
fi
