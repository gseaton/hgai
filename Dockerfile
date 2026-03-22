FROM python:3.11-slim

LABEL maintainer="HypergraphAI Contributors"
LABEL description="HypergraphAI - Semantic Hypergraph Knowledge Platform"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY hgai/ ./hgai/
COPY ui/ ./ui/
COPY shell/ ./shell/
COPY scripts/ ./scripts/

# Create non-root user
RUN useradd -m -u 1001 hgai && chown -R hgai:hgai /app
USER hgai

EXPOSE 8000

CMD ["uvicorn", "hgai.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
