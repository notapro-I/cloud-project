#!/bin/bash
set -e

# Start the Ollama server in the background
echo "Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for the server to be ready
sleep 2

# Pull the mistral model
echo "Pulling mistral model..."
ollama pull mistral

# Run mistral once to warm it up
echo "Warming up mistral model..."
ollama run mistral "ping"

echo "Ollama initialization complete. Mistral model ready."

# Keep the server running
wait $OLLAMA_PID
