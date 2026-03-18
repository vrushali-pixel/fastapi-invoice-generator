# ─────────────────────────────────────────────
# CONCEPT: Dockerfile
# A Dockerfile is a recipe for building a Docker image.
# Each line is a layer — Docker caches layers so
# rebuilds are fast if nothing changed.
#
# FROM: start from an existing image (Python 3.12)
# WORKDIR: set working directory inside container
# COPY: copy files from your machine into container
# RUN: execute commands during build
# CMD: command to run when container starts
# ─────────────────────────────────────────────

# Use official Python slim image — smaller than full Python
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# CONCEPT: Copy requirements first, then install
# Why not copy everything at once?
# Docker caches each layer. If you copy all files first,
# any file change invalidates the cache and reinstalls
# all packages. Copying requirements.txt first means
# packages only reinstall when requirements.txt changes.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the application code
COPY . .

# Create pdfs folder inside container
RUN mkdir -p pdfs

# CONCEPT: EXPOSE
# Documents which port the app listens on.
# Doesn't actually publish the port — that's done
# in docker-compose.yml with the ports setting.
EXPOSE 8000

# Command to run when container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]