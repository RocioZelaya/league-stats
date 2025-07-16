import os
import requests
from urllib.parse import urlencode

# Assumes your existing fetch-data.py is also deployed on the same Vercel app
VERCEL_APP_DOMAIN = os.environ.get("VERCEL_URL") # Vercel automatically sets this env var
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
                "Access-Control-Allow-Origin": "*" # Still needed for Neocities to fetch from THIS proxy
            },
            "body": {"error": "Game name and tag line are required."}
        }

    # Construct the URL to your existing fetch-data endpoint
    # Ensure VERCEL_APP_DOMAIN is correctly set (e.g., https://your-app-name.vercel.app)
    if not VERCEL_APP_DOMAIN:
        # Fallback for local development or if VERCEL_URL is not set
        # You might need to set this manually for local testing if not on Vercel
        VERCEL_APP_DOMAIN = "http://localhost:3000" # Or your Vercel public domain during dev
        print("Warning: VERCEL_URL not found, using fallback for internal proxy call.")


    target_url = f"{VERCEL_APP_DOMAIN}/api/fetch-data?{urlencode({'gameName': game_name, 'tagLine': tag_line})}"
    print(f"Proxying request to: {target_url}")

    try:
        # Make an internal request to your main fetch-data endpoint
        response = requests.get(target_url)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": data
        }
    except requests.exceptions.RequestException as e:
        print(f"Error during internal proxy request: {e}")
        status_code = e.response.status_code if e.response is not None else 500
        error_message = f"Proxy failed to fetch data: {e}"
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
