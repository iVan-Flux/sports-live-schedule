import datetime
import time
import json
from flask import Flask, render_template, request
import cloudscraper

app = Flask(__name__)

def fetch_live_matches_by_input(sport, date_str):
    scraper = cloudscraper.create_scraper()
    
    # --- ১. Session Warmup ---
    print("⏳ Warming up session (visiting sofascore.com)...")
    headers_warmup = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }
    try:
        scraper.get("https://www.sofascore.com", headers=headers_warmup, timeout=10)
        print("✅ Session warmed up successfully!")
    except Exception as e:
        print(f"⚠️ Warmup failed: {e}")

    # API রিকোয়েস্ট হেডার
    headers_api = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive"
    }

    # ইউজার থেকে আসা স্পোর্টস ও ডেট অনুযায়ী এপিআই ইউআরএল সেট
    urls_to_try = [
        f"https://www.sofascore.com/api/v1/sport/{sport}/scheduled-events/{date_str}",
        f"https://api.sofascore.com/api/v1/sport/{sport}/scheduled-events/{date_str}"
    ]

    response = None
    for url in urls_to_try:
        try:
            res = scraper.get(url, headers=headers_api, timeout=15)
            if res.status_code == 200:
                response = res
                print(f"✅ Success (200) for {sport.upper()} on {url}")
                break
            else:
                print(f"⚠️ Status {res.status_code} on {url}")
        except Exception as e:
            print(f"⚠️ Error on {url}: {e}")

    matches_list = []
    if response:
        try:
            events = response.json().get('events', [])
            seen_ids = set()
            for event in events:
                raw_id = str(event.get('id'))
                if raw_id in seen_ids:
                    continue

                league = event.get('tournament', {}).get('name')
                unique_id = event.get('tournament', {}).get('uniqueTournament', {}).get('id')
                event_ts = event.get('startTimestamp')
                start_dt = datetime.datetime.fromtimestamp(event_ts)

                team1_short = event.get('homeTeam', {}).get('shortName') or event.get('homeTeam', {}).get('name')
                team2_short = event.get('awayTeam', {}).get('shortName') or event.get('awayTeam', {}).get('name')

                # স্ট্যান্ডার্ড ডেট-টাইম ফরম্যাট
                match_time_readable = start_dt.strftime("%I:%M %p (%d-%b-%Y)")

                # এসেট ইউআরএল তৈরি
                league_logo = f"https://api.sofascore.com/api/v1/unique-tournament/{unique_id}/image/dark" if unique_id else ""
                team1_logo = f"https://api.sofascore.com/api/v1/team/{event.get('homeTeam', {}).get('id')}/image"
                team2_logo = f"https://api.sofascore.com/api/v1/team/{event.get('awayTeam', {}).get('id')}/image"

                match_data = {
                    "id": raw_id,
                    "leagueLogo": league_logo,
                    "leagueTitle": league,
                    "matchTime": match_time_readable,
                    "sportType": sport.upper(),
                    "team1Logo": team1_logo,
                    "team1Name": team1_short,
                    "team2Logo": team2_logo,
                    "team2Name": team2_short
                }
                matches_list.append(match_data)
                seen_ids.add(raw_id)

        except Exception as e:
            print(f"⚠️ Error parsing events: {e}")

    return matches_list

@app.route('/', methods=['GET'])
def index():
    sport = request.args.get('sport')
    date_str = request.args.get('date')
    
    matches = []
    if sport and date_str:
        matches = fetch_live_matches_by_input(sport, date_str)
    
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    return render_template('index.html', 
                           matches=matches, 
                           selected_sport=sport, 
                           selected_date=date_str, 
                           today_str=today_str)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7070)
