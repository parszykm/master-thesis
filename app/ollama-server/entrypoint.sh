#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &
# Record Process ID.
pid=$!

# Pause for Ollama to start.
sleep 5

echo "🔴 Retrieve sroecker/nuextract-tiny-v1.5 model..."
ollama pull sroecker/nuextract-tiny-v1.5
echo "🟢 Done!"

# Wait for Ollama process to finish.
wait $pid