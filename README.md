# CyberPUP Moderation Stack

CyberPUP is a Telegram group moderation stack consisting of two bots:
- **CyberPUP Security**: Automated ML spam checks, reputation tracking, and auto-ban enforcement.
- **CyberPUP Core**: Admin command suite with dual-emit logging (`/setlog`).

## Deployment Instructions

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cyberpup.git
   cd cyberpup
   ```
2. Create your `.env` file from the template:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` with your actual Telegram bot tokens and API keys.
4. Launch the stack with Docker Compose:
   ```bash
   docker compose up -d --build
   ```
