# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies (context is project root)
COPY services/agenda-engine/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code (context is project root)
COPY services/agenda-engine/src/ ./src/

# Copy shared_prompts from project root
COPY shared_prompts/ ./shared_prompts/

# Expose port
EXPOSE 8081

# Run
CMD ["python", "-m", "src.main"]
