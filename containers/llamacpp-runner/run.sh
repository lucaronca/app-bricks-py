#!/bin/bash

# Function to handle cleanup on SIGTERM
cleanup() {
    echo "SIGTERM received. Cleaning up..."
    # Kill background processes
    kill "$OLLAMA_PID" "$LLAMA_PID"
    exit 0
}

# Trap SIGTERM and SIGINT
trap cleanup SIGTERM SIGINT

echo "Starting Ollama serve..."
ollama serve &
OLLAMA_PID=$!

echo "Starting Llama server..."
# Add your specific flags here (model path, port, etc.)
/usr/local/bin/llama-server --models-dir /models &
LLAMA_PID=$!

echo "Processes started (Ollama: $OLLAMA_PID, Llama: $LLAMA_PID). Waiting..."

# Wait for background processes to keep the script running
wait
