import os
import requests
from urllib.parse import urlencode

# This dynamically gets your Vercel app's domain
VERCEL_APP_DOMAIN = os.environ.get("VERCEL_URL")
if VERCEL_APP_DOMAIN and not VERCEL_APP_DOMAIN.startswith("http"):
    VERCEL_APP_DOMAIN = f"https://{VERCEL_APP_DOMAIN}"

def handler(request):
    game_name = request.args.get('gameName')
    tag_line = request.args.get('tagLine')

    if not game_name or not tag_line:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": {"error": "Game name and tag line are required."}
        }

    # IMPORTANT: Ensure VERCEL_APP_DOMAIN is correctly set (e.g., https://your-app-name.vercel.app)
    # This will be used to call your main API endpoint (api/index.py) internally
    if not VERCEL_APP_DOMAIN:
        # Fallback for local development if VERCEL_URL is not automatically set
        VERCEL_APP_DOMAIN = "http://localhost:3000" # Adjust if your local dev server runs on a different port
        print("Warning: VERCEL_URL not found, using fallback for internal proxy call.")

    # Construct the URL to your *existing* main API endpoint (api/index.py)
    # This assumes api/index.py handles the gameName and tagLine parameters
    target_url = f"{VERCEL_APP_DOMAIN}/api/index?{urlencode({'gameName': game_name, 'tagLine': tag_line})}"
    print(f"Proxying request to: {target_url}")

    try:
        # Make an internal server-to-server request to your main API
        response = requests.get(target_url)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*" # Still needed for Neocities to fetch from THIS proxy
            },
            "body": data
        }
    except requests.exceptions.RequestException as e:
        print(f"Error during internal proxy request: {e}")
        # Capture the status code from the response if available
        status_code = e.response.status_code if e.response is not None else 500
        error_message = f"Proxy failed to fetch data from index.py: {e}"
        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": {"error": error_message}
        }
    except Exception as e:
        print(f"An unexpected error occurred in proxy: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": {"error": f"An unexpected error occurred: {str(e)}"}
        }
