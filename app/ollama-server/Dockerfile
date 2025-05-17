FROM ollama/ollama:latest

EXPOSE 11434

# Preload the model by starting the daemon temporarily, then killing it
RUN nohup ollama serve > /dev/null 2>&1 & \
    sleep 5 && \
    ollama pull sroecker/nuextract-tiny-v1.5 && \
    pkill ollama

# Keep the server running and reuse the preloaded model
CMD ["/bin/bash", "-c", "ollama serve"]
