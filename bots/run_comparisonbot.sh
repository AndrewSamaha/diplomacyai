#!/bin/bash

PAUSE_SECONDS=${1:-30}

echo "Running comparisonbot in loop with ${PAUSE_SECONDS}s pause between rounds."
echo "Press Ctrl+C to stop."
echo ""

while true; do
    uv run -m bots.comparisonbot
    echo ""
    echo "Sleeping ${PAUSE_SECONDS}s..."
    sleep "$PAUSE_SECONDS"
    echo ""
done
