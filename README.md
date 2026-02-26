# Crypto Upgrades Monitor

> **Note:** This README is AI generated. It may contain errors or omissions.

## Overview
Crypto Upgrades Monitor is an automated, serverless-ready architecture designed to track, ingest, and analyze potential tokenomics and protocol upgrades across various cryptocurrency projects. The system fetches signals from GitHub releases and official project blogs, uses LLM-powered relevance agents to filter and categorize the events, and publishes structured updates to a Supabase database.

A static, decoupled web dashboard provides a clean interface for filtering and reviewing the detected upgrades and their assessed confidence scores.

## Architecture

The project is split into two primarily decoupled segments:
1. **The Python Data Pipeline (`src/`)**: A background daemon that polls data sources, clusters related events, verifies them using Gemini AI models, and pushes final "canonical upgrades" to a Supabase Postgres instance via the REST API.
2. **The Static Frontend (`web/`)**: A zero-dependency vanity HTML/JS/CSS frontend that fetches real-time upgrade JSON payloads directly from the Supabase public API. This frontend can be hosted independently on any static site CDN (like Vercel).

## Setup & Local Development

### 1. Environment Variables
Copy `.env.example` to `.env` (if provided) or create your own `.env` file at the root of the project with the following secrets:
- `SUPABASE_URL`: Your Supabase project URL.
- `SUPABASE_KEY`: Your Supabase **service_role** key (required for the backend to UPSERT data).
- `GOOGLE_API_KEY`: API key for Google Gemini Pro (used by relevance/verification agents).
- `GITHUB_TOKEN`: Personal Access Token for GitHub API limits.
- `X_BEARER_TOKEN`: Twitter/X API access (if enabled).

### 2. Dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Running the Backend Daemon
Execute the following command to begin the polling cycle:
```bash
python -m src.main
```
This will start the infinite polling loop. The daemon will respect the `source_registry.yaml` configurations, scrape new events, update Supabase, and sleep between polling intervals.

### 4. Viewing the Frontend
To view the frontend locally, you can start a simple local server in the project root:
```bash
npx serve . 
# Or open web/index.html in a browser, but using a local dev server is recommended to avoid CORS if developing locally.
```
*Note: Because the frontend is fully decoupled, it fetches data securely from your real Supabase instance even when running locally.*

## Deployment

### Vercel (Frontend)
The `vercel.json` file in the root directory is configured strictly to deploy the `web/` folder as a static site.
1. Connect your repository to Vercel.
2. The deployment will automatically bypass python compilers and host your frontend globally.

### Local Backend Daemon
Currently, the backend data ingestion is designed to be run locally. Because the architecture is decoupled, your local computer acts as the worker node, securely pushing JSON payloads to the cloud Supabase database.
1. Leave `python -m src.main` running in a dedicated terminal window.
2. The daemon will wake up every hour, scrape new articles, process them, and update the live Vercel frontend.
