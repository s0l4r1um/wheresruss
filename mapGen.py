import folium
import json
import requests
import pwinput
import os
from datetime import date
from folium.features import DivIcon
from folium.plugins import AntPath
from folium.plugins import TimestampedGeoJson

# Init map

m = folium.Map([39.00,-95.00], zoom_start=5)

# Make live calls to AeroAPI for recent flights
callCount = 0
# uncomment for local protected API key passing:
#apiKey = pwinput.pwinput(prompt='API Key: ', mask='')
# only recommended to use the following in GitHub Actions:
apiKey = os.getenv("AEROAPI_KEY")
if not apiKey:
    apiKey = pwinput.pwinput(prompt='API Key: ', mask='')
    if not apiKey:
        raise ValueError("AEROAPI_KEY environment variable is not set")
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
    new_flights = flights_dict['flights']
    with open("flights.json", "r+") as f:
        old = json.load(f)
        old_flights = old['flights']
        for flight in old_flights:
            if flight not in new_flights:
                new_flights.append(flight)
        flights_dict['flights'] = new_flights
        f.seek(0)
        flights_str = json.dumps(flights_dict)
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

dir_list = os.listdir(track_path)
num_tracks = len(dir_list)
track = []
for track_file in dir_list:
    fname = "tracks/" + track_file
    with open(fname, "r") as f:
        json_data = json.load(f)
    track_poly = []
    track = []
    for json_dict in json_data['positions']:
        track_poly.append((json_dict['latitude'],json_dict['longitude']))
        latlong = []
        latlong.append(json_dict['longitude'])
        latlong.append(json_dict['latitude'])
        timestamp = json_dict['timestamp']
        track.append({"coordinates": latlong, "timestamp": timestamp})
    last_report = json_data['positions'][-1]
    timestamp = last_report['timestamp']
    folium.PolyLine(track_poly, tooltip=timestamp).add_to(m)
    
    ## TODO - figure out how to make this be selectfully displayed
    # # Convert track data to GeoJSON format
    # features = [
    #     {
    #         "type": "Feature",
    #         "geometry": {
    #             "type": "Point",
    #             "coordinates": point["coordinates"],
    #         },
    #         "properties": {
    #             "time": point["timestamp"],
    #             "icon": "marker",
    #             "iconstyle": {
    #                 "iconUrl": "paper-plane-icon.png",
    #                 "iconSize": [40, 40],
    #             }
    #         },
    #     }
    #     for point in track
    # ]
    # # Add TimestampedGeoJson to the map
    # TimestampedGeoJson(
    #     {"type": "FeatureCollection", "features": features},
    #     period="PT15M",  # Time interval between points
    #     add_last_point=False,
    #     auto_play=False,
    #     loop=True,
    #     max_speed=10,
    #     transition_time=100,
    #     duration="PT1M"
    # ).add_to(m)

last_flight = flight_ids[0]
fname = "tracks/" + last_flight + ".json"
with open(fname, "r") as f:
    json_data = json.load(f)
track = []
for json_dict in json_data['positions']:
    latlong = []
    latlong.append(json_dict['longitude'])
    latlong.append(json_dict['latitude'])
    timestamp = json_dict['timestamp']
    track.append({"coordinates": latlong, "timestamp": timestamp})

# Convert track data to GeoJSON format
features = [
    {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": point["coordinates"],
        },
        "properties": {
            "time": point["timestamp"],
            "icon": "marker",
            "iconstyle": {
                "iconUrl": "paper-plane-icon.png",
                "iconSize": [40, 40],
            }
        },
    }
    for point in track
]

# Add TimestampedGeoJson to the map
TimestampedGeoJson(
    {"type": "FeatureCollection", "features": features},
    period="PT15M",  # Time interval between points
    add_last_point=False,
    auto_play=True,
    loop=True,
    max_speed=10,
    transition_time=300,
    duration="PT1M"
).add_to(m)

# show layer group
folium.LayerControl().add_to(m)

print('Total API Calls = ', callCount)

m.save("index.html")
