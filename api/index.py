from http.server import BaseHTTPRequestHandler
import os
import requests
import json
from urllib.parse import urlparse, parse_qs
import datetime

RIOT_API_KEY = os.environ.get('RIOT_API_KEY')

def get_puuid(gameName, tagLine, api_key):
    link = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}?api_key={api_key}'
    response = requests.get(link)
    response.raise_for_status()
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

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def do_GET(self):
        status_code = 200
        response_body = {"message": "Hello from Vercel! Use /api/fetch-data with query parameters."}
        content_type = 'application/json'

        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        if not RIOT_API_KEY:
            status_code = 500
            response_body = {"error": "RIOT_API_KEY environment variable not set."}
        
        elif path == '/api/fetch-data':
            game_name = query_params.get('gameName', [None])[0]
            tag_line = query_params.get('tagLine', [None])[0]
            
            if not game_name or not tag_line:
                status_code = 400
                response_body = {"error": "Missing 'gameName' or 'tagLine' query parameter."}
            else:
                try:
                    puuid = get_puuid(game_name, tag_line, RIOT_API_KEY)

                    match_ids = get_match_ids(puuid, RIOT_API_KEY, count=1)
                    if not match_ids:
                        status_code = 404
                        response_body = {'error': 'No recent matches found for this player.'}
                    else:
                        latest_game_id = match_ids[0]
                        
                        match_data = get_match_data(latest_game_id, RIOT_API_KEY)
                        
                        player_game_info = None
                        for participant in match_data['info']['participants']:
                            if participant['puuid'] == puuid:
                                player_game_info = participant
                                break
                        
                        if not player_game_info:
                            status_code = 404
                            response_body = {'error': 'Player data not found in the latest match details.'}
                        else:
                            game_result = "Victory" if player_game_info['win'] else "Defeat"
                            champ_played = player_game_info['championName']
                            kills = player_game_info['kills']
                            deaths = player_game_info['deaths']
                            assists = player_game_info['assists']
                            kda = f"{kills}/{deaths}/{assists}"
                            champion_id_last_played = player_game_info['championId']
                            match_start_time = datetime.datetime.fromtimestamp(match_data['info']['gameStartTimestamp'] / 1000).strftime('%Y-%m-%d')
                            
                            champion_mastery_data = get_champion_mastery(puuid, champion_id_last_played, RIOT_API_KEY)
                            mastery_level = champion_mastery_data.get('championLevel', 'N/A')
                            mastery_points = champion_mastery_data.get('championPoints', 'N/A')
                            
                            response_body = {
                                'message': 'Data fetched successfully!',
                                'riotId': f"{game_name}#{tag_line}",
                                'puuid': puuid,
                                'latestMatch': {
                                    'id': latest_game_id,
                                    'gameResult': game_result,
                                    'championPlayed': champ_played,
                                    'kda': kda,
                                    'startTime': match_start_time
                                },
                                'championMastery': {
                                    'championId': champion_id_last_played,
                                    'level': mastery_level,
                                    'points': mastery_points
                                }
                            }
                            status_code = 200
                
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code if e.response is not None else 500
                    response_body = {"error": f"Riot API Error: {e.response.text if e.response else str(e)}"}
                except Exception as e:
                    status_code = 500
                    response_body = {"error": f"An internal server error occurred: {str(e)}"}
        else:
            status_code = 404
            response_body = {"error": "Not Found. Use /api/fetch-data."}
        
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Security-Policy', "default-src *; frame-ancestors https://dapond.neocities.org;")
        self.wfile.write(json.dumps(response_body).encode('utf-8'))
        return
