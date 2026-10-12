FROM python:3.11-slim

# Install system dependencies (including graphviz for agent workflow diagrams)
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY adk_multiagent_systems/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir google-adk && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy project files (existing code remains 100% untouched)
COPY adk_utils /app/adk_utils
COPY adk_multiagent_systems /app/adk_multiagent_systems

# Environment settings
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_GENAI_USE_VERTEXAI=False
ENV PYTHONPATH=/app:/app/adk_multiagent_systems

WORKDIR /app/adk_multiagent_systems

EXPOSE 8010

# Starts ADK web on 0.0.0.0 so it is reachable from host machine
CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8010"]
