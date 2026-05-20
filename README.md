Image Security Scanning

What is a CVE?
CVE = Common Vulnerabilities and Exposures — a public database of known security flaws in software. Every vulnerability gets an ID like CVE-2024-12345 and a severity score:

```
CRITICAL   → Exploit exists, remote code execution possible
HIGH       → Serious impact, likely exploitable
MEDIUM     → Exploitable under specific conditions
LOW        → Minimal impact
NEGLIGIBLE → Theoretical, almost no real risk
```

When you ship a Docker image, you're responsible for every CVE in every package inside it — even ones you didn't install directly.

How Scanners Work
Tools like Trivy work by:

```
1. Extracting your image layers
2. Inventorying every package (apt, pip, npm, etc.)
3. Checking each package version against CVE databases
4. Reporting which packages have known vulnerabilities
         ↓
   Your fastapi:v1 image might have 200+ CVEs
   Your fastapi:v3 slim image might have 20
   Your fastapi:v4 alpine image might have 5
```

Step 1 — Install Trivy

Step 2 — Scan your images from Week 1

```
# Update vulnerability database first
trivy image --download-db-only

# Scan your images — watch the numbers change with each version
trivy image fastapi:v1
trivy image fastapi:v2
trivy image fastapi:v3
trivy image fastapi:v4
```

Step 3 — Understand the output
Trivy output looks like this:

```
fastapi:v3 (debian 12.5)
════════════════════════════════════════
Total: 24 (UNKNOWN: 0, LOW: 16, MEDIUM: 5, HIGH: 3, CRITICAL: 0)

┌─────────────────┬──────────────┬──────────┬────────────────┬───────────────┐
│    Library      │ Vulnerability│ Severity │ Installed Ver  │  Fixed Ver    │
├─────────────────┼──────────────┼──────────┼────────────────┼───────────────┤
│ libssl3         │ CVE-2024-xxx │ HIGH     │ 3.0.11         │ 3.0.13        │
│ pip             │ CVE-2023-xxx │ MEDIUM   │ 23.0.1         │ 23.1.2        │
└─────────────────┴──────────────┴──────────┴────────────────┴───────────────┘
```

Key columns:

Library — which package has the vulnerability
Vulnerability — the CVE ID (look it up at cve.mitre.org)
Severity — how bad it is
Installed Ver — what you have
Fixed Ver — what you need to upgrade to

Step 4 — Filter to what actually matters

```
# Only show HIGH and CRITICAL — ignore noise
trivy image --severity HIGH,CRITICAL fastapi:v3

# Show only fixable vulnerabilities
trivy image --severity HIGH,CRITICAL \
  --ignore-unfixed fastapi:v3

# Scan your production URL shortener image
cd ~/projects/url-shortener
trivy image --severity HIGH,CRITICAL \
  --ignore-unfixed url-shortener-app-1 2>/dev/null || \
trivy image --severity HIGH,CRITICAL \
  --ignore-unfixed \
  $(docker compose images -q app)
```

--ignore-unfixed is key for CI pipelines — don't fail builds for vulnerabilities that have no fix yet.

Step 5 — Scan beyond the image (filesystem, config)

```
# Scan your project filesystem for vulnerabilities in dependencies
trivy fs --severity HIGH,CRITICAL ~/projects/url-shortener

# Scan your requirements.txt directly
trivy fs --severity HIGH,CRITICAL \
  ~/projects/url-shortener/app/requirements.txt

# Scan for misconfigurations in your Dockerfile
trivy config ~/projects/url-shortener/Dockerfile

# Scan docker-compose.yml for misconfigs
trivy config ~/projects/url-shortener/docker-compose.yml
```

The config scanner catches things like:

Running as root
No healthcheck defined
Privileged containers
Secrets in environment variables

Step 6 — Generate a report

```
# JSON report for CI/CD integration
trivy image --format json \
  --output trivy-report.json \
  --severity HIGH,CRITICAL \
  fastapi:v3

# See the structured output
cat trivy-report.json | python3 -m json.tool | head -50

# SARIF format (for GitHub Security tab)
trivy image --format sarif \
  --output trivy-report.sarif \
  --severity HIGH,CRITICAL \
  fastapi:v3

# Summary table only
trivy image --format table \
  --severity HIGH,CRITICAL \
  --ignore-unfixed \
  fastapi:v3
```

Step 7 — Fix vulnerabilities by updating base image
The most common fix is simply using a newer base image:

```
# Dockerfile — pin to a specific digest for reproducibility
# First, find the latest digest
# FROM python:3.11-slim   ← floating tag, changes over time

# Better — use a recent specific version
FROM python:3.11.9-slim

# Rebuild with updated base
docker build -f Dockerfile.v3 -t fastapi:v3-updated \
  --no-cache .

# Compare CVE counts before and after
trivy image --severity HIGH,CRITICAL fastapi:v3
trivy image --severity HIGH,CRITICAL fastapi:v3-updated
```

Often just rebuilding with --no-cache pulls a fresh base image and eliminates many CVEs.

Step 8 — Add scanning to your Compose workflow
Create a scan script you run before every deployment:

```
cat > ~/projects/url-shortener/scan.sh << 'EOF'
#!/bin/bash
set -e

IMAGE=$(docker compose images -q app)
echo "🔍 Scanning image: $IMAGE"

trivy image \
  --severity HIGH,CRITICAL \
  --ignore-unfixed \
  --exit-code 1 \
  $IMAGE

echo "✅ No HIGH/CRITICAL vulnerabilities found"
EOF

chmod +x ~/projects/url-shortener/scan.sh

# Run it
cd ~/projects/url-shortener
./scan.sh
```

--exit-code 1 makes Trivy exit with failure if vulnerabilities are found — this is what blocks a CI pipeline.

Step 9 — Docker Scout (built-in alternative)

```
# Docker Scout is built into newer Docker versions
docker scout cves fastapi:v3

# Quick overview
docker scout quickview fastapi:v3

# Compare two images
docker scout compare fastapi:v1 fastapi:v3
```

Step 10 — Scan a public image before pulling it

```
# Always scan before using a new base image
trivy image --severity HIGH,CRITICAL python:3.11-slim
trivy image --severity HIGH,CRITICAL nginx:alpine
trivy image --severity HIGH,CRITICAL redis:7-alpine

# Compare slim vs alpine security posture
trivy image --severity HIGH,CRITICAL python:3.11-slim \
  2>&1 | tail -5
trivy image --severity HIGH,CRITICAL python:3.11-alpine \
  2>&1 | tail -5
```