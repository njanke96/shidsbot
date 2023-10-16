FROM debian:bullseye-slim

# System packages
RUN apt-get update -y && \
    apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    libffi-dev \
    python3-dev \
    libopus0 \
    libopus-dev

# copy code
WORKDIR /app
COPY shidsbot/ /app/shidsbot
COPY pyproject.toml /app
COPY docker-entrypoint.sh /app
RUN chmod +x docker-entrypoint.sh

# python packages
RUN pip install .

ENTRYPOINT /app/docker-entrypoint.sh

# Additional args can be passed to docker run
