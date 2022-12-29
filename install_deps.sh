#!/bin/bash

apt update && apt install ffmpeg libffi-dev python3-dev libopus0 libopus-dev

pip install .
