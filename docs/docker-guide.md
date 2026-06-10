# Docker Guide — Altiostar 5G MRO Pipeline

## Prerequisites
- Docker Desktop installed and running (green "Engine running" status)
- Repository cloned locally

## Build the Image
```bash
docker build -t altiostar-pipeline .
```
Build time: ~10 minutes on first run (downloads Python + installs dependencies).
Subsequent builds are faster due to layer caching.

## Run the Pipeline (Tests)
```bash
docker run altiostar-pipeline
```
Expected output: all tests passing (260/260).

## Run with Local Data (Volume Mount)
```bash
docker run -v "$(pwd)/data:/app/data" altiostar-pipeline
```
On Windows:
```bash
docker run -v "%cd%/data:/app/data" altiostar-pipeline
```

## Rebuild After Code Changes
```bash
docker build -t altiostar-pipeline .
docker run altiostar-pipeline
```

## Troubleshooting
**Error: cannot connect to Docker daemon**
→ Open Docker Desktop and wait for "Engine running" status, then retry.

**Tests fail inside container but pass locally**
→ Check that all new files are committed — Docker copies from the repo, not your working directory.