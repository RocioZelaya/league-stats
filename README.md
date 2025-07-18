## League Stats Vercel App

This project is a simple League of Legends stats dashboard deployed on Vercel with the purpose of displaying it as an iframe in my neocities website. It fetches my latest match and champion mastery using the Riot Games API and displays them.

### Features
- Fetches and displays my(or possibly yours too) latest LoL match stats (match ID, outcome, champion, KDA, time)
- Shows champion mastery level and points for your last played champion
- Stylish, responsive frontend using only HTML/CSS/JS
- Serverless Python API (Vercel Function) for Riot API calls

### Project Structure

- `public/index.html` — Main frontend UI (served at the root URL)
- `api/index.py` — Python backend for fetching data from Riot API
- `requirements.txt` — Python dependencies (requests)
- `vercel.json` — Vercel deployment configuration

### Setup & Deployment

1. **Riot API Key:**
   - Set the `RIOT_API_KEY` environment variable in your Vercel project settings.

2. **Directory Structure:**
   - Place your static files in `public/` (e.g., `public/index.html`).
   - Place your API code in `api/` (e.g., `api/index.py`).

3. **Deploy:**
   - Push to your Git repository connected to Vercel, or use the Vercel CLI.
   - Vercel will automatically build and deploy your app.

4. **Access:**
   - Visit your Vercel deployment URL to see the dashboard.

### Notes
- No need to manually add static file routes in `vercel.json`—Vercel serves everything in `public/` at the root.
- The API endpoint is `/api/index` (do not use relative paths).
- Only `requests` is required in `requirements.txt` for the current backend code.

---

Deployed with vercel at: https://league-stats-two.vercel.app/
Made with ❤️ for League of Legends stat tracking!