from datetime import datetime, time
import pathlib
import json
import requests

path = pathlib.Path(__file__).parent.resolve()

with open(f'{path}/.data.json') as f:
    bearer = json.load(f)['bearer']

with open(f'{path}/settings.json') as f:
    settings = json.load(f)

teams = list(settings["teams"])

def get_headers(bearer):
    return {
      'Accept': 'application/vnd.api+json',
      'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
      'Authorization': f'Bearer {bearer}',
    }

slots = settings["slots"]

stella_id = "25349"
customer_ids = [stella_id]

response = requests.get(
    f'https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/customers?cache[save]=false&include=allEvents%2CteamRequests%2CcustomerNotes%2Cmemberships&filterRelations[teamRequests][accepted]=true&filterRelations[eventRegistrations][is_free_trial]=true&company=copa',
    headers=get_headers(bearer)
)

if response.status_code not in range(200, 299):
    # Assume we need to refresh auth token

    token_payload = {
        "grant_type": "client_credentials",
        "client_id": settings["client_id"],
        "client_secret": settings["client_secret"],
        "stay_signed_in": False,
        "company": "copa",
        "company_code": "copa"
    }

    token_response = requests.post(
        'https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/customer/auth/token?company=copa',
        json=token_payload
    )
    token_json = token_response.json()
    bearer = token_json["access_token"]

    with open(f'{path}/.data.json', 'w') as f:
        json.dump({"bearer": bearer}, f)

    response = requests.get(
        f'https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/customers?cache[save]=false&include=allEvents%2CteamRequests%2CcustomerNotes%2Cmemberships&filterRelations[teamRequests][accepted]=true&filterRelations[eventRegistrations][is_free_trial]=true&company=copa',
        headers=get_headers(bearer)
    )

customers = [x for x in response.json()["data"] if x["type"] == "customer" and x["id"] in customer_ids]

registered_events = [event["id"].split("-")[1] for customer in customers for event in customer["relationships"]["allEvents"]["data"]]

for team in teams:
    team_id = settings["teams"][team]
    response = requests.get(
            f'https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/teams/{team_id}?cache\[save\]=false&include=registrableEvents.summary&filterRelations\[registrableEvents\]\[publish\]=true&company=copa',
            headers=get_headers(bearer)
    )

    resp = response.json()
    event_summaries = [
        event for event in resp['included'] if event['type'] == 'event-summary'
    ]

    for event in event_summaries:
        attributes = event['attributes']
        if event["id"] in registered_events:
            continue
        if not attributes['registration_status'] == 'open':
            continue
        start_datetime = datetime.fromisoformat(attributes['start_date'])
        start_time = start_datetime.time()
        end_time = datetime.fromisoformat(attributes['end_date']).time()
        weekday = start_datetime.weekday()

        for slot in slots:
            if team not in slot["teams"]:
                continue
            if "date" in slot and not start_datetime.date() == datetime.fromisoformat(slot["date"]).date():
                continue
            if "day_of_week" in slot and not start_datetime.weekday() == slot["day_of_week"]:
                continue
            if start_time < time(*map(int, slot["start_time"].split(":"))):
                continue
            if end_time > time(*map(int,slot["end_time"].split(":"))):
                continue

            print(f'{attributes["name"]}, {start_datetime.strftime("%A %m/%d")} {start_time.strftime("%H:%M")}-{end_time.strftime("%H:%M")}, {attributes["open_slots"]} slots')
            break
