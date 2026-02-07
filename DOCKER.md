# 🐳 VIVOHOME AI - Docker Deployment Guide

## Quick Start

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- NVIDIA GPU with 15GB+ VRAM
- NVIDIA Docker runtime

### 1. Install NVIDIA Docker Runtime

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### 2. Deploy with Docker Compose

```bash
# Clone repository
git clone https://github.com/yourusername/vivohome-ai.git
cd vivohome-ai

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access app
open http://localhost:7860
```

### 3. Stop Services

```bash
docker-compose down
```

---

## Manual Docker Build

### Build Image

```bash
docker build -t vivohome-ai:latest .
```

### Run Container

```bash
# Run Gradio app (requires vLLM running separately)
docker run -d \
  --name vivohome-gradio \
  -p 7860:7860 \
  -e VLLM_URL=http://host.docker.internal:8000 \
  vivohome-ai:latest
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Docker Compose Stack            │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐   ┌──────────────┐  │
│  │   vLLM       │   │   Gradio     │  │
│  │   Server     │◄──┤   Web App    │  │
│  │              │   │              │  │
│  │  Port: 8000  │   │  Port: 7860  │  │
│  └──────────────┘   └──────────────┘  │
│         │                   │          │
│         │                   │          │
│    ┌────▼───────────────────▼────┐    │
│    │   vivohome-network (bridge) │    │
│    └─────────────────────────────┘    │
│                                         │
└─────────────────────────────────────────┘
```

---

## Environment Variables

### vLLM Service
- `CUDA_VISIBLE_DEVICES`: GPU device ID (default: 0)

### Gradio Service
- `VLLM_URL`: vLLM server URL (default: http://vllm:8000)

---

## Troubleshooting

### Issue: GPU not detected
```bash
# Verify NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

### Issue: vLLM fails to start
```bash
# Check GPU memory
nvidia-smi

# Reduce GPU memory utilization
# Edit docker-compose.yml: --gpu-memory-utilization 0.7
```

### Issue: Port already in use
```bash
# Find process using port
lsof -i :7860
lsof -i :8000

# Kill process or change port in docker-compose.yml
```

---

## Production Deployment

### AWS EC2 (g5.xlarge or larger)

```bash
# 1. Launch EC2 instance with Deep Learning AMI
# 2. Install Docker + NVIDIA runtime (pre-installed in DLAMI)
# 3. Clone repo and run docker-compose

# 4. Configure security group
# - Allow inbound: 7860 (Gradio), 8000 (vLLM - optional)

# 5. Access via public IP
http://<EC2_PUBLIC_IP>:7860
```

### Google Cloud (n1-standard-4 + T4 GPU)

```bash
# Similar to AWS, use GCP Deep Learning VM
gcloud compute instances create vivohome-ai \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=pytorch-latest-gpu \
  --image-project=deeplearning-platform-release
```

---

## Performance Optimization

### Reduce Image Size

```dockerfile
# Use multi-stage build
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 AS builder
# ... build steps ...

FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04
COPY --from=builder /app /app
```

### Enable BuildKit

```bash
DOCKER_BUILDKIT=1 docker build -t vivohome-ai:latest .
```

---

## Monitoring

### View Container Stats

```bash
docker stats vivohome-vllm vivohome-gradio
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f gradio
docker-compose logs -f vllm
```

---

## Backup & Restore

### Backup Database

```bash
docker cp vivohome-gradio:/app/vivohome.db ./backup/
```

### Restore Database

```bash
docker cp ./backup/vivohome.db vivohome-gradio:/app/
```

---

**Built with ❤️ for VIVOHOME Electronics**
