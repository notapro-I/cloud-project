FROM ollama/ollama:0.3.12

# Create a shell script to pull and run mistral on startup
RUN mkdir -p /ollama

COPY entrypoint.sh /ollama/entrypoint.sh
RUN chmod +x /ollama/entrypoint.sh

ENTRYPOINT ["/ollama/entrypoint.sh"]
