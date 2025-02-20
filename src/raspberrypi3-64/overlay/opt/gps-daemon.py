import serial
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


#* ========================================================================================================================================= *#
#* =========================================== JSON GPS DATA TYPE / LOGGER / PARSERS / CHECKSUMS =========================================== *#


SHARED_FILE_PATH = '/tmp/gps_data.json'
LOG_FILE_PATH = '/tmp/gps_daemon.log'

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)

def nmea_to_decimal(nmea: str, direction: str) -> Optional[float]:
    """Convert NMEA latitude/longitude to decimal degrees."""
    if not nmea or not direction:
        return None
    if '.' not in nmea:
        return None

    split_index = nmea.index('.') - 2
    degrees = int(nmea[:split_index])
    minutes = float(nmea[split_index:])
    decimal = degrees + (minutes / 60)
    if direction in ['S', 'W']:
        decimal = -decimal

    return round(decimal, 6)


def format_gps_time(raw_time: str, raw_date: Optional[str] = None, #! 2 - ROMANIA HOUR OFFSET
                    offset_hours: Optional[int] = 2, offset_minutes: Optional[int] = 0) -> str:
    """
    Format GPS time to ISO 8601 format (e.g., 2024-12-15T12:26:15+02:00).
    Handles time with optional date and timezone offsets.
    """
    hours = int(raw_time[:2])
    minutes = int(raw_time[2:4])
    seconds = float(raw_time[4:])

    if raw_date and len(raw_date) == 6:
        day = int(raw_date[:2])
        month = int(raw_date[2:4])
        year = int(raw_date[4:]) + 2000
    else:
        return f"{hours:02}:{minutes:02}:{seconds:.3f}Z"

    utc_time = datetime(year, month, day, hours, minutes, int(seconds), int((seconds % 1) * 1_000_000))
    total_offset = timedelta(hours=offset_hours, minutes=offset_minutes)
    local_time = utc_time + total_offset

    return local_time.isoformat() + f"{offset_hours:+03}:{offset_minutes:02}"


#* =========================================== JSON GPS DATA TYPE / LOGGER / PARSERS / CHECKSUMS =========================================== *#
#* ========================================================================================================================================= *#
#* ===========================================                   GPS FORMAT                      =========================================== *#


def parse_gpgga(parts: List[str]) -> Dict[str, Any]:
    """Parses GGA sentence (Time, Position, Fix Type Data)."""
    return {
        'type': 'GGA',
        'time': format_gps_time(parts[1]),
        'latitude': nmea_to_decimal(parts[2], parts[3]),
        'longitude': nmea_to_decimal(parts[4], parts[5]),
        'fix_quality': int(parts[6]) if parts[6].isdigit() else None,
        'num_satellites': int(parts[7]) if parts[7].isdigit() else None,
        'hdop': float(parts[8]) if parts[8] else None,
        'altitude': f"{parts[9]} {parts[10]}" if len(parts) > 10 else None,
        'geoid_separation': f"{parts[11]} {parts[12]}" if len(parts) > 12 else None,
        'age_of_diff_corr': parts[13] if len(parts) > 13 else None,
        'station_id': parts[14].split('*')[0] if len(parts) > 14 else None,
    }


def parse_gpgsa(parts: List[str]) -> Dict[str, Any]:
    """Parses GSA sentence (DOP and Active Satellites)."""
    satellites_used = [parts[i] for i in range(3, 15) if parts[i]]
    return {
        'type': 'GSA',
        'mode': parts[1],
        'fix_type': parts[2],
        'satellites_used': satellites_used,
        'pdop': parts[15],
        'hdop': parts[16],
        'vdop': parts[17].split('*')[0],
    }


def parse_gpgsv(parts: List[str]) -> Dict[str, Any]:
    """Parses GSV sentence (Satellites in View)."""
    return {
        'type': 'GSV',
        'num_messages': parts[1],
        'message_number': parts[2],
        'num_satellites': parts[3],
    }


def parse_gprmc(parts: List[str]) -> Dict[str, Any]:
    """Parses RMC sentence (Recommended Minimum Data)."""

    def format_date(raw_date: str) -> str:
        if len(raw_date) == 6:
            return f"{raw_date[:2]}.{raw_date[2:4]}.{raw_date[4:]}"  # DD.MM.YY
        return "Invalid Date"

    return {
        'type': 'RMC',
        'time': format_gps_time(parts[1]),
        'status': parts[2],
        'latitude': nmea_to_decimal(parts[3], parts[4]),
        'longitude': nmea_to_decimal(parts[5], parts[6]),
        'speed': float(parts[7]) if parts[7] else None,
        'course': float(parts[8]) if parts[8] else None,
        'date': format_date(parts[9]),
        'magnetic_variation': f"{parts[10]} {parts[11]}" if len(parts) > 11 else None,
    }


def parse_gpvtg(parts: List[str]) -> Dict[str, str]:
    """Parses VTG sentence (Course and Speed)."""
    return {
        'type': 'VTG',
        'course_true': parts[1],
        'reference_true': parts[2],
        'course_magnetic': parts[3],
        'reference_magnetic': parts[4],
        'speed_knots': parts[5],
        'unit_knots': parts[6],
        'speed_kmh': parts[7],
        'unit_kmh': parts[8].split('*')[0],
    }


def parse_gpzda(parts: List[str]) -> Dict[str, Any]:
    """
    Parses ZDA sentence (Date and Time) into structured data.

    Example ZDA sentence: $GPZDA,172809.456,12,07,1996,00,00*45
    """
    raw_time = parts[1]  # UTC time (HHMMSS.ss)
    day = parts[2]       # Day
    month = parts[3]     # Month
    year = parts[4]      # Year

    offset_hours = 0
    offset_minutes = 0

    if len(parts) > 5:
        offset_hours = int(parts[5].strip())
    if len(parts) > 6:
        offset_minutes = int(parts[6].split('*')[0].strip())
    
    raw_date = f"{day}{month}{year}"
    formatted_time = format_gps_time(raw_time, raw_date, offset_hours, offset_minutes)

    return {
        'type': 'ZDA',
        'time': formatted_time,
        'day': int(day),
        'month': int(month),
        'year': int(year),
        'local_time_offset': f"{offset_hours:+03}:{offset_minutes:02}"
    }
    

def parse_gpgll(parts: List[str]) -> Dict[str, Any]:
    """Parses GLL sentence (Geographic Position - Latitude/Longitude)."""
    return {
        'type': 'GLL',
        'latitude': nmea_to_decimal(parts[1], parts[2]),
        'longitude': nmea_to_decimal(parts[3], parts[4]),
        'time': format_gps_time(parts[5]),
        'status': parts[6],
        'mode': parts[7].split('*')[0] if len(parts) > 7 else None,
    }


def parse_gphdt(parts: List[str]) -> Dict[str, Any]:
    """Parses HDT sentence (Heading True)."""
    return {
        'type': 'HDT',
        'heading': float(parts[1]),
        'status': parts[2].split('*')[0] if len(parts) > 2 else None,
    }
    

#* ===========================================                   GPS FORMAT                      =========================================== *#
#* ========================================================================================================================================= *#
#* ===========================================                   GPS DAEMON                      =========================================== *#


PARSERS = {
    '$GPGGA': (lambda parts: parse_gpgga(parts), 15),  # GGA: Global Positioning System Fix Data
    '$GPGSA': (lambda parts: parse_gpgsa(parts), 18),  # GSA: GNSS DOP and Active Satellites
    '$GPGSV': (lambda parts: parse_gpgsv(parts), 20),  # GSV: GNSS Satellites in View
    '$GPRMC': (lambda parts: parse_gprmc(parts), 12),  # RMC: Recommended Minimum Specific GNSS Data
    '$GPVTG': (lambda parts: parse_gpvtg(parts), 9),   # VTG: Course Over Ground and Ground Speed
    '$GPZDA': (lambda parts: parse_gpzda(parts), 7),   # ZDA: Time & Date (UTC format type)
    '$GPGLL': (lambda parts: parse_gpgll(parts), 8),   # GLL: Geographic Position - Latitude/Longitude
    '$GPHDT': (lambda parts: parse_gphdt(parts), 3),   # HDT: Heading - True
}


def parse_gps_line(line: str) -> Dict[str, Any]:
    """Routes NMEA sentence to the appropriate parser."""
    if not line:
        logging.debug("Skipping empty line.")
        return {}

    parts = line.split(',')
    logging.debug(f"Split NMEA Sentence: {parts}")

    if not parts or len(parts[0]) == 0:
        logging.warning("Invalid or empty NMEA sentence header.")
        return {}

    parser, expected_count = PARSERS.get(parts[0], (None, 0))

    if not parser:
        logging.error(f"Unsupported NMEA sentence type: {parts[0]}")
        return {'error': 'Unsupported NMEA sentence'}

    if len(parts) < expected_count:
        logging.error(f"Insufficient fields for {parts[0]}. Expected {expected_count}, got {len(parts)}.")
        return {'error': 'Insufficient fields'}

    try:
        return parser(parts)
    except Exception as e:
        logging.error(f"Error parsing {parts[0]}: {e}")
        return {'error': f"Parsing error: {e}"}


def gps_daemon() -> None:
    """Runs the GPS daemon to update the JSON file."""
    gps_data = {}

    try:
        with serial.Serial('/dev/ttyUSB0', baudrate=9600, timeout=1) as ser:
            while True:
                line = ser.readline().decode('ascii', errors='ignore').strip()
                if not line:
                    logging.debug("Skipping empty or invalid line.")
                    continue

                parsed_data = parse_gps_line(line)
                if 'error' in parsed_data:
                    logging.warning(f"Skipping invalid data: {parsed_data}")
                    continue

                if parsed_data:
                    gps_data[parsed_data['type']] = parsed_data
                    logging.debug(f"Parsed GPS Data: {json.dumps(gps_data, indent=4)}")
                    with open(SHARED_FILE_PATH, 'w') as file:
                        json.dump(gps_data, file, indent=4)

                time.sleep(1)

    except serial.SerialException as e:
        logging.critical(f"Serial port error: {e}")
    except Exception as e:
        logging.critical(f"Unexpected error: {e}")


if __name__ == '__main__':
    gps_daemon()


#* ===========================================                   GPS DAEMON                      =========================================== *#
#* ========================================================================================================================================= *#
