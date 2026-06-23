import datetime
import time
from flask import Flask, render_template
import cloudscraper

app = Flask(__name__)

# ৪টি প্রধান খেলার তালিকা
SPORTS_LIST = ["football", "cricket", "basketball", "ice-hockey"]

def fetch_live_matches():
    scraper = cloudscraper.create_scraper()
    now = datetime.datetime.now()
    end_window = now + datetime.timedelta(hours=24)
    start_ts = now.timestamp()
    end_ts = end_window.timestamp()

    dates_to_check = sorted(list(set([now.date(), end_window.date()])))
    seen_ids = set()
    matches_list = []

    for sport in SPORTS_LIST:
        for d in dates_to_check:
            date_str = d.strftime("%Y-%m-%d")
            url = f"https://api.sofascore.com/api/v1/sport/{sport}/scheduled-events/{date_str}"

            try:
                response = scraper.get(url)
                if response.status_code == 200:
                    events = response.json().get('events', [])
                    for event in events:
                        event_ts = event.get('startTimestamp')
                        # ২৪ ঘণ্টার উইন্ডো চেক
                        if not (start_ts <= event_ts < end_ts):
                            continue

                        raw_id = str(event.get('id'))
                        if raw_id in seen_ids:
                            continue

                        league = event.get('tournament', {}).get('name')
                        unique_id = event.get('tournament', {}).get('uniqueTournament', {}).get('id')

                        start_dt = datetime.datetime.fromtimestamp(event_ts)
                        team1_short = event.get('homeTeam', {}).get('shortName') or event.get('homeTeam', {}).get('name')
                        team2_short = event.get('awayTeam', {}).get('shortName') or event.get('awayTeam', {}).get('name')

                        # সময় ফরম্যাট
                        match_time_readable = start_dt.strftime("%I:%M %p (%d-%b)")

                        match_data = {
                            "leagueLogo": f"https://api.sofascore.com/api/v1/unique-tournament/{unique_id}/image/dark" if unique_id else None,
                            "leagueTitle": league,
                            "matchTime": match_time_readable,
                            "sportType": sport.upper(),
                            "team1Logo": f"https://api.sofascore.com/api/v1/team/{event.get('homeTeam', {}).get('id')}/image",
                            "team1Name": team1_short,
                            "team2Logo": f"https://api.sofascore.com/api/v1/team/{event.get('awayTeam', {}).get('id')}/image",
                            "team2Name": team2_short
                        }
                        matches_list.append(match_data)
                        seen_ids.add(raw_id)

            except Exception as e:
                print(f"Error fetching {sport}: {e}")

            time.sleep(0.1)
    return matches_list

@app.route('/')
def index():
    matches = fetch_live_matches()
    # খেলা অনুযায়ী গ্রুপ করা
    grouped_matches = {}
    for match in matches:
        sport = match['sportType']
        if sport not in grouped_matches:
            grouped_matches[sport] = []
        grouped_matches[sport].append(match)
    return render_template('index.html', grouped_matches=grouped_matches)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
