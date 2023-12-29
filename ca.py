from datetime import datetime, time
import pathlib
import json
import requests

path = pathlib.Path(__file__).parent.resolve()

with open(f'{path}/settings.json') as f:
    bearer = json.load(f)['bearer']

headers = {
  'Accept': 'application/vnd.api+json',
  'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
  'Authorization': f'Bearer {bearer}',
}

winter_9to11_training = 2611
winter_9to11_speedlab = 2638
winter_9to11_gameplay = 2672
teams = [winter_9to11_training, winter_9to11_speedlab, winter_9to11_gameplay]

slots = [{
    'day_of_week': 0,
    'start_time': "16:20",
    'end_time': "17:50",
}]

for team in teams:
    response = requests.get(
            f'https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/teams/{team}?cache\[save\]=false&include=registrableEvents.summary&filterRelations\[registrableEvents\]\[publish\]=true&company=copa',
            headers=headers
    )

    resp = response.json()
    event_summaries = [
        event for event in resp['included'] if event['type'] == 'event-summary'
    ]

    for event in event_summaries:
        attributes = event['attributes']
        if not attributes['registration_status'] == 'open':
            continue
        start_datetime = datetime.fromisoformat(attributes['start_date'])
        start_time = start_datetime.time()
        end_time = datetime.fromisoformat(attributes['end_date']).time()
        weekday = start_datetime.weekday()

        for slot in slots:
            if not start_datetime.weekday() == slot["day_of_week"]:
                continue
            if start_time < time(*map(int, slot["start_time"].split(":"))):
                continue
            if end_time > time(*map(int,slot["end_time"].split(":"))):
                continue

            print(f'{attributes["name"]}, {start_datetime.strftime("%A")} {start_time.strftime("%H:%M")}-{end_time.strftime("%H:%M")}, {attributes["open_slots"]} slots')
            break
