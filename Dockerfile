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
COPY .env /app
COPY pyproject.toml /app

# python packages
RUN pip install .

ENTRYPOINT python3 /app/shidsbot/main.py

# Additional args can be passed to docker run
