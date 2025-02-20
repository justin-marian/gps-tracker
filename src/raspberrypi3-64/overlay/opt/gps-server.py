from flask import Flask, render_template, jsonify
import json
import logging
from typing import Dict, Any

app = Flask(__name__)

#!!! KEY !!! 
#! You have images to show you where to get the API Key

#! Use your own Google Cloud API Key for Maps JavaScript API
#! For securing the API_KEY / SECRET_KEY for your repo on GitHub

#! Create an .env file that will be ignored by git
#! The API_KEY must be added in the index.html file too at 
#! <script async defer src="https://maps.googleapis.com/maps/api/js?key=<API_KEY>initMap"></script>
#! API_KEY has to end in character '='

#! No secret key is needed for this project
#!!! KEY !!!
API_KEY = ...
SECRET_KEY = ...

SHARED_FILE_PATH = '/tmp/gps_data.json'
LOG_FILE_PATH = '/tmp/gps_server.log'

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)

DEFAULT_GPS_DATA = {
    'GGA': {
        'latitude': 'Unknown',
        'longitude': 'Unknown',
        'altitude': 'Unknown',
        'num_satellites': 'Unknown',
        'fix_quality': 'Unknown',
        'hdop': 'Unknown',
        'geoid_separation': 'Unknown',
        'age_of_diff_corr': 'Unknown',
        'station_id': 'Unknown',
    },
    'GSA': {
        'mode': 'Unknown',
        'fix_type': 'Unknown',
        'satellites_used': [],
        'pdop': 'Unknown',
        'hdop': 'Unknown',
        'vdop': 'Unknown',
    },
    'GSV': {
        'num_messages': 'Unknown',
        'message_number': 'Unknown',
        'num_satellites': 'Unknown',
    },
    'RMC': {
        'time': 'Unknown',
        'status': 'Unknown',
        'latitude': 'Unknown',
        'longitude': 'Unknown',
        'speed': 'Unknown',
        'course': 'Unknown',
        'date': 'Unknown',
        'magnetic_variation': 'Unknown',
    },
    'VTG': {
        'course_true': 'Unknown',
        'reference_true': 'Unknown',
        'course_magnetic': 'Unknown',
        'reference_magnetic': 'Unknown',
        'speed_knots': 'Unknown',
        'unit_knots': 'Unknown',
        'speed_kmh': 'Unknown',
        'unit_kmh': 'Unknown',
    },
    'ZDA': {
        'time': 'Unknown',
        'day': 'Unknown',
        'month': 'Unknown',
        'year': 'Unknown',
        'local_time_offset': 'Unknown',
    },
    'GLL': {
        'latitude': 'Unknown',
        'longitude': 'Unknown',
        'time': 'Unknown',
        'status': 'Unknown',
        'mode': 'Unknown',
    },
    'HDT': {
        'heading': 'Unknown',
        'status': 'Unknown',
    }
}


def read_gps_data() -> Dict[str, Any]:
    """ Reads GPS data from the shared JSON file. """
    try:
        with open(SHARED_FILE_PATH, 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        logging.warning("Shared file not found, returning default data.")
        return DEFAULT_GPS_DATA
    except json.JSONDecodeError:
        logging.error("Corrupted GPS data in the shared file.")
        return {'error': 'Corrupted data'}


@app.route('/')
def index() -> str:
    """Renders the index page with real-time GPS data."""
    try:
        gps_data = read_gps_data()
        return render_template('index.html', gps_data=gps_data)
    except Exception as e:
        logging.error(f"Error rendering index page: {e}")
        return "Error rendering page", 500


@app.route('/api/gps', methods=['GET'])
def get_gps_data():
    """Returns GPS data as JSON."""
    try:
        gps_data = read_gps_data()
        return jsonify(gps_data)
    except Exception as e:
        logging.error(f"Error fetching GPS data: {e}")
        return jsonify({'error': 'Error fetching GPS data'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
