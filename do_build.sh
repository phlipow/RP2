#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "=== CLEAN BUILD STARTING ==="
echo "Removing old build files..."
rm -f main.aux main.bbl main.bcf main.blg main.log main.out main.pdf main.run.xml

echo "Running pdflatex pass 1..."
pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1

echo "Running biber..."
biber main > /dev/null 2>&1

echo "Running pdflatex pass 2..."
pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1

echo "Running pdflatex pass 3..."
pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1

echo ""
echo "=== BUILD COMPLETE ==="
echo ""
echo "Checking results..."
echo ""

if [ -f "main.pdf" ]; then
    PDFSIZE=$(stat -c%s main.pdf)
    echo "✓ main.pdf exists: $PDFSIZE bytes"
    
    PAGES=$(pdfinfo main.pdf 2>/dev/null | grep "Pages:" | awk '{print $2}')
    echo "✓ PDF Pages: $PAGES"
else
    echo "✗ main.pdf NOT FOUND"
fi

echo ""
echo "Biber summary:"
grep -E "INFO|WARN" main.blg | tail -5

echo ""
echo "Checking for LaTeX errors in main.log..."
if grep -q "Runaway argument\|LaTeX Error\|Fatal" main.log; then
    echo "✗ ERRORS FOUND:"
    grep -A2 "Runaway argument\|LaTeX Error\|Fatal" main.log | head -20
else
    echo "✓ No major errors in main.log"
fi
