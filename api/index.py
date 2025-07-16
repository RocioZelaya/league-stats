import os
import requests
import pandas as pd
import datetime
import pygsheets
import json # To parse the service account key from environment variable
from http.server import BaseHTTPRequestHandler

# --- Configuration (These will come from request or Vercel ENV) ---
# For Vercel, sensitive info like API keys are best stored as Environment Variables.
# These will be set in your Vercel project settings.
RIOT_API_KEY = os.environ.get('RIOT_API_KEY')
GOOGLE_SERVICE_ACCOUNT_KEY = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY') # JSON content as string

# --- Helper Functions for Riot API (mostly from your existing code) ---
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

# --- Google Sheets Integration Function ---
def write_to_google_sheet(data, spreadsheet_name, worksheet_name, service_account_key_json):
    """
    Writes a list of data (e.g., [["Header1", "Header2"], ["Value1", "Value2"]]) to a Google Sheet.
    """
    try:
        # Authenticate with Google Sheets using the service account key JSON
        gc = pygsheets.service_account(client_secret=service_account_key_json)
        
        # Open the spreadsheet
        sh = gc.open(spreadsheet_name)
        
        # Select the worksheet
        wks = sh.worksheet_by_title(worksheet_name)
        
        # Append data starting from the next available row
        wks.append_table(data) # This will append new rows
        
        return {"status": "success", "message": "Data written to Google Sheet successfully."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to write to Google Sheet: {str(e)}"}

# --- Vercel Serverless Function Handler ---
# This is the function Vercel will call when your API endpoint is hit.
# It expects a request object and should return a response object.
def handler(request, response):
    # This example assumes a GET request for simplicity,
    # and expects gameName and tagLine as query parameters.
    # e.g., YOUR_VERCEL_APP/api/fetch_riot_data?gameName=remildisculpas&tagLine=rem

    if request.method != 'GET':
        response.status_code = 405
        response.headers['Content-Type'] = 'application/json'
        response.json({'error': 'Method Not Allowed'})
        return

    gameName = request.args.get('gameName')
    tagLine = request.args.get('tagLine')
    spreadsheet_name = request.args.get('spreadsheetName', 'RiotDataLog') # Default sheet name
    worksheet_name = request.args.get('worksheetName', 'MatchData')    # Default worksheet name

    if not gameName or not tagLine:
        response.status_code = 400
        response.headers['Content-Type'] = 'application/json'
        response.json({'error': 'Missing gameName or tagLine query parameters.'})
        return

    if not RIOT_API_KEY:
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        response.json({'error': 'Riot API Key not configured in Vercel Environment Variables.'})
        return

    if not GOOGLE_SERVICE_ACCOUNT_KEY:
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        response.json({'error': 'Google Service Account Key not configured in Vercel Environment Variables.'})
        return

    try:
        # Parse the JSON string from the environment variable into a Python dict
        service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_KEY)

        # 1. Get PUUID
        puuid = get_puuid(gameName, tagLine, RIOT_API_KEY)

        # 2. Get Latest Match ID
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

        # Prepare data for Google Sheet
        # Example: One row per execution, appending to sheet
        data_to_sheet = [
            ["Timestamp", "Game Name", "Tag Line", "Match ID", "Game Result", "Champion", "KDA", "Mastery Level", "Mastery Points"]
        ]
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

    except requests.exceptions.RequestException as e:
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        response.json({'error': f'Riot API Error: {e.response.text if e.response else e}'})
    except json.JSONDecodeError:
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        response.json({'error': 'Invalid Google Service Account Key JSON in environment variables.'})
    except Exception as e:
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        response.json({'error': f'An unexpected error occurred: {str(e)}'})
