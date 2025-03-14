from datetime import datetime, time
import sys
import pathlib
import json
import requests

path = pathlib.Path(__file__).parent.resolve()

def log(s):
    return print(s, file=sys.stderr)

def str_to_time(v):
    return time(*map(int, v.split(":")))

def fits_in_time_range(event_start, event_end, range_start, range_end):
    if event_start < range_start:
        return False
    if event_end > range_end:
        return False
    return True

def overlaps_time_range(event_start, event_end, range_start, range_end):
    if event_start < range_end and event_end > range_start:
        return True
    return False

def fits_in_slot(event_start, event_end, slot):
    return fits_in_time_range(
        event_start,
        event_end,
        str_to_time(slot["start_time"]),
        str_to_time(slot["end_time"]),
    )

def overlaps_slot(event_start, event_end, slot):
    return overlaps_time_range(
        event_start,
        event_end,
        str_to_time(slot["start_time"]),
        str_to_time(slot["end_time"]),
    )

with open(f'{path}/.data.json') as f:
    bearer = json.load(f)['bearer']

with open(f'{path}/settings.json') as f:
    settings = json.load(f)

slots = list(filter(
    lambda slot: not ("disabled" in slot and slot["disabled"]),
    settings["slots"],
))
queried_teams = [ team for slot in slots for team in slot['teams'] ]

teams = list(filter(
    lambda team: team in queried_teams,
    settings["teams"],
))

id_to_team = { v: k for k, v in settings["teams"].items() }

def get_headers(bearer):
    return {
      'Accept': 'application/vnd.api+json',
      'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
      'Authorization': f'Bearer {bearer}',
    }

customer_ids = [str(v) for k, v in settings["customers"].items()]


log('Fetching registrations...')
response = requests.get(
    f'https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/customers?cache[save]=false&include=allEvents%2CteamRequests%2CcustomerNotes%2Cmemberships&filterRelations[teamRequests][accepted]=true&filterRelations[eventRegistrations][is_free_trial]=true&company=copa',
    headers=get_headers(bearer)
)


if response.status_code not in range(200, 299):
    log('failed.')

    # Assume we need to refresh auth token

    token_payload = {
        "grant_type": "client_credentials",
        "client_id": settings["client_id"],
        "client_secret": settings["client_secret"],
        "stay_signed_in": False,
        "company": "copa",
        "company_code": "copa"
    }

    log('Refreshing auth token')
    token_response = requests.post(
        'https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/customer/auth/token?company=copa',
        json=token_payload
    )
    token_json = token_response.json()
    bearer = token_json["access_token"]

    log('Saving new auth token...')
    with open(f'{path}/.data.json', 'w') as f:
        json.dump({"bearer": bearer}, f)
    log('done.')

    log('Requesting registrations...')
    response = requests.get(
        f'https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/customers?cache[save]=false&include=allEvents%2CteamRequests%2CcustomerNotes%2Cmemberships&filterRelations[teamRequests][accepted]=true&filterRelations[eventRegistrations][is_free_trial]=true&company=copa',
        headers=get_headers(bearer)
    )

if response.status_code not in range(200, 299):
    log('failed.')
    exit(1)

log('done.')

response_json = response.json()
customers = [x for x in response_json["data"] if x["type"] == "customers" and x["id"] in customer_ids]
customer_events = {x["id"]: x for x in response_json["included"] if x["type"] == "customer-events"}

registered_customer_event_ids = [event["id"] for customer in customers for event in customer["relationships"]["allEvents"]["data"]]
registered_event_ids = [customer_event_id.split("-")[1] for customer_event_id in registered_customer_event_ids]

log("Looking for registered events in slots...")
for slot in slots:

    slot["registered_customer_events"] = []
    for ce_id in registered_customer_event_ids:
        customer_event = customer_events[ce_id]["attributes"]
        start_datetime = datetime.fromisoformat(customer_event["start"])
        start_time = start_datetime.time()
        end_time = datetime.fromisoformat(customer_event["end"]).time()
        team_id = int(customer_event["hteam_id"])
        if not team_id in id_to_team:
            continue
        if not overlaps_slot(start_time, end_time, slot):
            continue
        if not id_to_team[team_id] in slot["teams"]:
            continue
        slot["registered_customer_events"].append(customer_event)
log("Done")

for team in teams:
    team_id = settings["teams"][team]
    log(f'Fetching team {team} available slots')
    response = requests.get(
            f'https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/teams/{team_id}?cache[save]=false&include=registrableEvents.summary&filterRelations[registrableEvents][publish]=true&company=copa',
            headers=get_headers(bearer)
    )

    try:
        resp = response.json()
    except Exception as e:
        print(f'Exception for team {team} with response {response}')
        continue

    if 'included' not in resp:
        print(f'No sessions in team {team}')
        continue

    event_summaries = [
        event for event in resp['included'] if event['type'] == 'event-summaries'
    ]

    for event in event_summaries:
        attributes = event['attributes']
        if event["id"] in registered_event_ids:
            continue
        if not attributes['registration_status'] == 'open':
            continue
        start_datetime = datetime.fromisoformat(attributes['start_date'])
        start_date = start_datetime.date()
        start_time = start_datetime.time()
        end_time = datetime.fromisoformat(attributes['end_date']).time()
        weekday = start_datetime.weekday()

        for slot in slots:
            if not team in slot["teams"]:
                continue
            if "date" in slot and not start_date == datetime.fromisoformat(slot["date"]).date():
                continue
            if "exclude" in slot and start_date in [datetime.fromisoformat(d).date() for d in slot["exclude"]]:
                continue
            if "day_of_week" in slot and not start_datetime.weekday() == slot["day_of_week"]:
                continue
            if not fits_in_slot(start_time, end_time, slot):
                continue

            remaining_teams = slot["teams"].copy()
            # Check if any of the other registered events for this slot
            # is higher priority
            for registered_customer_event in slot["registered_customer_events"]:
                if start_date != datetime.fromisoformat(registered_customer_event["start"]).date():
                    continue

                registered_team = id_to_team[int(registered_customer_event["hteam_id"])]
                if not registered_team in remaining_teams:
                    continue
                idx = remaining_teams.index(registered_team)
                remaining_teams = remaining_teams[:idx]

            if not team in remaining_teams:
                continue

            print(f'{attributes["name"]}, {start_datetime.strftime("%A %m/%d")} {start_time.strftime("%H:%M")}-{end_time.strftime("%H:%M")}, {attributes["open_slots"]} slots')
            break
