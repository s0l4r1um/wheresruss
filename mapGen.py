import folium
import json
import requests
import pwinput
import os
from datetime import date
from folium.features import DivIcon

# Init map

m = folium.Map([39.00,-95.00], zoom_start=5)

# Make live calls to AeroAPI for recent flights
callCount = 0
# uncomment for local protected API key passing:
#apiKey = pwinput.pwinput(prompt='API Key: ', mask='')
# only recommended to use the following in GitHub Actions:
apiKey = os.environ["AEROAPI_KEY"]
apiUrl = "https://aeroapi.flightaware.com/aeroapi/"

ident = 'N785RW'
payload = {'max_pages': 2}
auth_header = {'x-apikey':apiKey}

print('Grabbing latest flights...')
response = requests.get(apiUrl + f"flights/{ident}",
    params=payload, headers=auth_header)
callCount += 1
if response.status_code == 200:
    flights_dict = response.json()
    flights_str = json.dumps(flights_dict)
    with open("flights.json", "w") as f:
        f.write(flights_str)
    authOk = 1
else:
    print("Error executing request")

# Parse flight ids from api return

flight_ids = []
for json_dict in flights_dict['flights']:
    flight_ids.append(json_dict['fa_flight_id'])

# Make live calls to AeroAPI for flight track data per flight

path = os.getcwd()
track_path = path + "/tracks/"
dir_list = os.listdir(track_path)
for flight_id in flight_ids:
    # Skip API call if flight has already been saved
    search_name = flight_id + ".json"
    if search_name not in dir_list:
        print('Found new flight ', flight_id, ' - querying and recording...')
        response = requests.get(apiUrl + f"flights/{flight_id}/track", headers=auth_header)
        callCount += 1
        if response.status_code == 200:
            track_dict = response.json()
            track_str = json.dumps(track_dict)
            fname = "tracks/" + flight_id + ".json"
            with open(fname, "w") as f:
                f.write(track_str)
        else:
            print("Error executing request")
    else:
        print('Skipping flight ', flight_id, ', already logged')

# Pin last arrival location
        
last_flight = flight_ids[0]
fname = "tracks/" + last_flight + ".json"
with open(fname, "r") as f:
    json_data = json.load(f)
last_report = json_data['positions'][-1]
last_lat = last_report['latitude']
last_long = last_report['longitude']
folium.Marker(location=[last_lat,last_long], icon=folium.Icon(color='green', icon='plane', prefix='fa')).add_to(m)

# Record last updated date on map

today = date.today()

folium.map.Marker(
    [25.00, -90.00],
    icon=DivIcon(
        icon_size=(150,36),
        icon_anchor=(0,0),
        html='<div style="font-size: 12pt">Last Updated On {today}</div>'.format(today=today),
        )
    ).add_to(m)

if authOk:
    folium.map.Marker(
        [25.00, -97.00],
        icon=DivIcon(
            icon_size=(150,36),
            icon_anchor=(0,0),
            html='<div style="font-size: 12pt">Auth Success</div>',
            )
        ).add_to(m)
        
# Map all tracks

for track_file in dir_list:
    with open(track_file, "r") as f:
        json_data = json.load(f)
    track = []
    for json_dict in json_data['positions']:
        track.append((json_dict['latitude'],json_dict['longitude']))
    folium.PolyLine(track, tooltip="Coast").add_to(m)

print('Total API Calls = ', callCount)

m.save("index.html")