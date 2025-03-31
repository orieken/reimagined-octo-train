FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Install Python dependencies (these will be overridden by the mount)
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Install invoke task runner
RUN pip install --no-cache-dir invoke

# Create necessary directories
RUN mkdir -p /workspace/app/data

# Install development tools
RUN pip install --no-cache-dir ipython pytest-xdist

# Set Python path
ENV PYTHONPATH=/workspace

# Set up a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# Give permissions to the workspace
RUN chown -R $USERNAME:$USERNAME /workspace
