FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install BendSQL
RUN curl -LJO https://github.com/datafuselabs/bendsql/releases/latest/download/bendsql-x86_64-unknown-linux-musl.tar.gz \
    && tar -xzf bendsql-x86_64-unknown-linux-musl.tar.gz \
    && mv bendsql /usr/local/bin/ \
    && chmod +x /usr/local/bin/bendsql \
    && rm bendsql-x86_64-unknown-linux-musl.tar.gz

# Install Python dependencies
RUN pip install --no-cache-dir \
    jinja2 \
    pandas \
    datetime

# Create working directory
WORKDIR /app

# Copy source files
COPY entrypoint.sh /app/
COPY src/ /app/src/
COPY templates/ /app/templates/
COPY sql/ /app/sql/

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]