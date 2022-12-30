#!/bin/sh

# Without this, python does not receive shutdown signals from docker.
exec python3 /app/shidsbot/main.py
