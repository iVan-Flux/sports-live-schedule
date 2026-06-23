import datetime
import time
from flask import Flask, render_template
import cloudscraper

app = Flask(__name__)

# --- STRICT LEAGUES ---
STRICT_LEAGUES = {
    "England": ["Premier League", "Championship", "League One", "League Two", "FA Cup", "EFL Cup"],
    "Spain": ["LaLiga", "LaLiga 2", "Copa del Rey", "Supercopa de España"],
    "Germany": ["Bundesliga", "2. Bundesliga", "DFB Pokal"],
    "Italy": ["Serie A", "Serie B", "Coppa Italia"],
    "France": ["Ligue 1", "Ligue 2", "Coupe de France"],
    "Turkey": ["Trendyol Süper Lig", "Türkiye Kupası"],
    "Portugal": ["Liga Portugal", "Taça de Portugal"],
    "Netherlands": ["Eredivisie", "KNVB Beker"],
    "Belgium": ["Pro League"],
    "Argentina": ["Liga Profesional de Fútbol", "Copa de la Liga Profesional"],
    "Brazil": ["Brasileirão Série A", "Copa do Brasil"],
    "USA": ["MLS", "US Open Cup"],
    "Saudi Arabia": ["Saudi Pro League", "King's Cup"],
    "India": ["Super League", "I-League"],
    "Bangladesh": ["Bangladesh Premier League"],
    "Australia": ["A-League Men", "Australia Cup"]
}

# --- PARTIAL MATCH LEAGUES ---
PARTIAL_LEAGUES = [
    "World Cup", "Olympic Games", "Club World Cup",
    "European Championship", "UEFA Nations League", "Copa América",
    "Africa Cup of Nations", "CONCACAF Gold Cup", "AFC Asian Cup",
    "UEFA Champions League", "UEFA Europa League", "UEFA Conference League", "UEFA Super Cup",
    "AFC Champions League", "AFC Cup",
    "CONMEBOL Libertadores", "CONMEBOL Sudamericana", "CONCACAF Champions Cup",
    "CAF Champions League", "CAF Confederation Cup"
]

CRICKET_VIP_KEYWORDS = ["World Cup", "Asia Cup", "Indian Premier League", "WPL", "BPL", "Pakistan Super League", "BBL", "The Hundred", "CPL", "SA20", "ILT20", "LPL", "Test Series", "ODI", "T20I", "International", "Tour"]
CRICKET_BLOCKLIST = ["Division", "Plate", "Club", "XI", "Academy", "U19", "List A", "Second XI", "Provincial", "Trophy", "Shield"]
OTHER_VIP = ["NBA", "NHL"]
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
                        if not (start_ts <= event_ts < end_ts):
                            continue

                        raw_id = str(event.get('id'))
                        if raw_id in seen_ids:
                            continue

                        league = event.get('tournament', {}).get('name')
                        category = event.get('tournament', {}).get('category', {}).get('name')

                        is_vip = False

                        if sport == 'football':
                            if category in STRICT_LEAGUES:
                                if league in STRICT_LEAGUES[category]:
                                    is_vip = True

                            if not is_vip:
                                for keyword in PARTIAL_LEAGUES:
                                    if keyword.lower() in league.lower():
                                        is_vip = True
                                        break

                        elif sport == 'cricket':
                            is_blocked = False
                            for bad in CRICKET_BLOCKLIST:
                                if bad.lower() in league.lower():
                                    is_blocked = True
                                    break
                            if not is_blocked:
                                for good in CRICKET_VIP_KEYWORDS:
                                    if good.lower() in league.lower():
                                        is_vip = True
                                        break

                        elif league in OTHER_VIP:
                            is_vip = True

                        if not is_vip:
                            continue

                        start_dt = datetime.datetime.fromtimestamp(event_ts)
                        unique_id = event.get('tournament', {}).get('uniqueTournament', {}).get('id')

                        team1_short = event.get('homeTeam', {}).get('shortName') or event.get('homeTeam', {}).get('name')
                        team2_short = event.get('awayTeam', {}).get('shortName') or event.get('awayTeam', {}).get('name')

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
    # Group matches by sport type to display nicely
    grouped_matches = {}
    for match in matches:
        sport = match['sportType']
        if sport not in grouped_matches:
            grouped_matches[sport] = []
        grouped_matches[sport].append(match)
    return render_template('index.html', grouped_matches=grouped_matches)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
