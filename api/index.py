from http.server import BaseHTTPRequestHandler
import os
import requests
import json
from urllib.parse import urlparse, parse_qs

import pygsheets

RIOT_API_KEY = os.environ.get('RIOT_API_KEY')
GOOGLE_SERVICE_ACCOUNT_KEY = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')


def get_puuid(gameName, tagLine, api_key):
    link = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}?api_key={api_key}'
    response = requests.get(link)
    response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
    return response.json()['puuid']

def get_match_ids(puuid, api_key, count=1):
    link = f'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}&api_key={api_key}'
    response = requests.get(link)
    response.raise_for_status()
    return response.json()

def get_match_data(match_id, api_key):
    link = f'https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={api_key}'
    response = requests.get(link)
    response.raise_for_status()
    return response.json()

def get_champion_mastery(puuid, champion_id, api_key):
    link = f'https://la2.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{champion_id}?api_key={api_key}'
    response = requests.get(link)
    response.raise_for_status()
    return response.json()

# --- Helper Function for Google Sheets (Define this outside the class) ---
# Example:
def append_to_google_sheet(data_to_append, google_service_account_key_str, spreadsheet_name, worksheet_name='Sheet1'):
    try:
        # Authenticate using the service account key JSON string
        gc = pygsheets.service_account(client_secret=json.loads(google_service_account_key_str))
        
        # Open the spreadsheet and select the worksheet
        sh = gc.open(spreadsheet_name)
        wks = sh.worksheet_by_title(worksheet_name)
        
        # Append data as a new row
        wks.append_table(values=[data_to_append], start='A1', end=None, dimension='ROWS', overwrite=False, include_empty=False)
        return True, "Data appended successfully."
    except Exception as e:
        return False, f"Failed to append to Google Sheet: {str(e)}"

# --- Main Vercel Handler Class ---
class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        # Default response values
        status_code = 200
        response_body = {"message": "Hello from Vercel! Use /api/fetch-data with query parameters."}
        content_type = 'application/json'

        # Parse the URL to get path and query parameters
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # --- Handle CORS Preflight (OPTIONS method) ---
        if self.command == 'OPTIONS':
            self.send_response(204) # No Content
            self.send_header('Access-Control-Allow-Origin', '*') # Adjust for production
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Access-Control-Max-Age', '86400') # Cache preflight for 24 hours
            self.end_headers()
            return

        # --- Check for RIOT_API_KEY and GOOGLE_SERVICE_ACCOUNT_KEY ---
        if not RIOT_API_KEY:
            status_code = 500
            response_body = {"error": "RIOT_API_KEY environment variable not set."}
        elif not GOOGLE_SERVICE_ACCOUNT_KEY:
            status_code = 500
            response_body = {"error": "GOOGLE_SERVICE_ACCOUNT_KEY environment variable not set."}
        
        # --- Handle your specific API route ---
        elif path == '/api/fetch-data':
            game_name = query_params.get('gameName', [None])[0]
            tag_line = query_params.get('tagLine', [None])[0]
            
            if not game_name or not tag_line:
                status_code = 400
                response_body = {"error": "Missing 'gameName' or 'tagLine' query parameter."}
            else:
                try:
                    # 1. Fetch PUUID
                    puuid = get_puuid(game_name, tag_line, RIOT_API_KEY)

                    # 2. Fetch Match IDs
                    match_ids = get_match_ids(puuid, RIOT_API_KEY, count=1) # Fetching 1 match ID for example

                    if match_ids:
                        latest_match_id = match_ids[0]

                        match_ids = get_match_ids(puuid, RIOT_API_KEY, count=1)
                    if not match_ids:
                        response.status_code = 404
                        response.headers['Content-Type'] = 'application/json'
                        response.json({'error': 'No recent matches found for this player.'})
                        return
                    latest_game_id = match_ids[0]
            
                    # 3. Get Detailed Match Data
                    match_data = get_match_data(latest_game_id, RIOT_API_KEY)
                    
                    player_game_info = None
                    for participant in match_data['info']['participants']:
                        if participant['puuid'] == puuid:
                            player_game_info = participant
                            break
            
                    if not player_game_info:
                        response.status_code = 404
                        response.headers['Content-Type'] = 'application/json'
                        response.json({'error': 'Player data not found in the latest match details.'})
                        return
                    
                    # Extract game info
                    game_result = "Victory" if player_game_info['win'] else "Defeat"
                    champ_played = player_game_info['championName']
                    kills = player_game_info['kills']
                    deaths = player_game_info['deaths']
                    assists = player_game_info['assists']
                    kda = f"{kills}/{deaths}/{assists}"
                    champion_id_last_played = player_game_info['championId']
                    match_start_time = datetime.datetime.fromtimestamp(match_data['info']['gameStartTimestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            
                    # 4. Get Champion Mastery
                    champion_mastery_data = get_champion_mastery(puuid, champion_id_last_played, RIOT_API_KEY)
                    mastery_level = champion_mastery_data.get('championLevel', 'N/A')
                    mastery_points = champion_mastery_data.get('championPoints', 'N/A')
                        
                         data_to_sheet = [["Timestamp", "Game Name", "Tag Line", "Match ID", "Game Result", "Champion", "KDA", "Mastery Level", "Mastery Points"]]
        # Append only if it's the first time, or make sure headers aren't re-added
        # For simplicity here, we'll append. You might need logic to check if headers exist.
        
                    data_to_sheet.append([
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        gameName,
                        tagLine,
                        latest_game_id,
                        game_result,
                        champ_played,
                        kda,
                        mastery_level,
                        mastery_points
                    ])
                    
                    # Write to Google Sheet
                    sheet_result = write_to_google_sheet(data_to_sheet, spreadsheet_name, worksheet_name, service_account_info)
            
                    # Return success response
                    response.status_code = 200
                    response.headers['Content-Type'] = 'application/json'
                    response.json({
                        'message': 'Data fetched and logged successfully.',
                        'gameResult': game_result,
                        'championPlayed': champ_played,
                        'kda': kda,
                        'championMasteryLevel': mastery_level,
                        'championMasteryPoints': mastery_points,
                        'googleSheetStatus': sheet_result['status'],
                        'googleSheetMessage': sheet_result['message']
                    })
                        response_body = {"message": "Riot ID and Match ID fetched, Google Sheet integration placeholder.", "riotId": f"{game_name}#{tag_line}", "puuid": puuid, "latestMatchId": latest_match_id}
                        status_code = 200

                    else:
                        status_code = 404
                        response_body = {"error": "No match IDs found for the given Riot ID."}

                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code if e.response is not None else 500
                    response_body = {"error": f"Riot API Error: {e.response.text if e.response else str(e)}"}
                except Exception as e:
                    status_code = 500
                    response_body = {"error": f"An unexpected error occurred: {str(e)}"}
        else:
            # Handle other paths not explicitly defined
            status_code = 404
            response_body = {"error": "Not Found. Use /api/fetch-data."}
        
        # --- Send the HTTP Response ---
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.end_headers()
        self.wfile.write(json.dumps(response_body).encode('utf-8'))
        return
