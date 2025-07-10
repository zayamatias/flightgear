import socket
import struct
import time
import math
import numpy as np
from scipy.spatial.transform import Rotation as R
import random

# Constants
MSG_MAGIC = 0x46474653  # 'FGFS' in hex
PROTO_VER = 0x00010001
POS_DATA_ID = 7
MAX_CALLSIGN_LEN = 8
MAX_PACKET_SIZE = 8192

class AIModel:
    def __init__(self):
        self.callsign = ''
        self.model_name = ''
        self.time = 0
        self.lag = 0 
        self.gx = 0
        self.gy = 0
        self.gz = 0
        self.orix = 1.0
        self.oriy = 0
        self.oriz = 0
        self.linearVel = (0, 0, 0)
        self.angularVel = (0, 0, 0)
        self.linearAccel = (0, 0, 0)
        self.angularAccel = (0, 0, 0)
        self.v2_properties = {}
        self.latitude_deg = None
        self.longitude_deg = None
        self.altitude_m = None
        self.airspeed_kt = None
        self.altitude_ft = None
        self.transponder_id = None
        self.heading_deg = None
        self.fixed_center_lat = None
        self.fixed_center_lon = None
        self.turn_direction = 1
        self.turn_rate_deg_per_sec = 3.0
        self.time_val = 0
        self.vertical_speed_fpm = 0
        self.posx = None
        self.posy = None
        self.posz = None
        self.rpm = 0.0  # Engine revolutions per minute
        self.chat = ""  # Chat message to be sent to the server

    def __repr__(self):
        return (f"AIModel(callsign={self.callsign}, model_name={self.model_name}, time={self.time}, lag={self.lag}, "
                f"gx={self.gx}, gy={self.gy}, gz={self.gz}, orix={self.orix}, oriy={self.oriy}, oriz={self.oriz}, "
                f"airspeed_kt={self.airspeed_kt}, altitude_ft={self.altitude_ft}, v2_properties={self.v2_properties}, "
                f"heading_deg={self.heading_deg}, turn_direction={self.turn_direction}, turn_rate_deg_per_sec={self.turn_rate_deg_per_sec}, vertical_speed_fpm={self.vertical_speed_fpm})")


# Helper to create the message header
def create_msg_header(callsign, msg_id, msg_len, requested_range_nm=100, reply_port=0):
    callsign_bytes = callsign.encode('ascii')[:8]
    callsign_bytes = callsign_bytes.ljust(8, b'\0')
    # Correct header order: magic, proto_ver, msg_id, msg_len, range, reply_port, callsign
    return struct.pack('!6I8s', MSG_MAGIC, PROTO_VER, msg_id, msg_len, requested_range_nm, reply_port, callsign_bytes)

def send_fg_position(airplane, host, port):
    """
    Send a FlightGear V2 position message using an AIModel object.
    Calculates orientation, position, v2_properties, and time inside.
    Handles network errors gracefully and retries on next call.
    """
    import socket
    # Use a global or module-level socket for efficiency
    if not hasattr(send_fg_position, "sock"):
        send_fg_position.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock = send_fg_position.sock
    # Update time
    airplane.time_val = time.time()
    # Calculate orientation and position
    orientation=(airplane.orix, airplane.oriy, airplane.oriz,)
    pos = (airplane.posx,airplane.posy,airplane.posz)
    # V2 properties
    v2_properties = [
        (10, 2, 'short'),
        (302, int(airplane.rpm), 'float'),
        (800, int(airplane.rpm), 'float')
    ]
    # Build and send packet
    model = airplane.model_name.encode('ascii')[:96]
    model = model.ljust(96, b'\0')
    fmt = '!96s2d3d3f3f3f3f3f'
    payload = struct.pack(fmt, model, airplane.time_val, airplane.lag, *pos, *orientation, *airplane.linearVel, *airplane.angularVel, *airplane.linearAccel, *airplane.angularAccel)
    v2_block = b''
    for prop_id, value, enc in v2_properties:
        if enc == 'short':
            v2_block += struct.pack('!HH', prop_id, 2)  # LEN=2 bytes
            v2_block += struct.pack('!h', value)
        elif enc == 'int':
            v2_block += struct.pack('!HH', prop_id, 4)  # LEN=4 bytes
            v2_block += struct.pack('!i', value)
        elif enc == 'float':
            v2_block += struct.pack('!HH', prop_id, 4)  # LEN=4 bytes
            v2_block += struct.pack('!f', value)
        elif enc == 'string':
            if isinstance(value, str) and value:
                s = value.encode('utf-8')
                length = len(s)
                v2_block += struct.pack('!HH', prop_id, length)
                v2_block += s
    pos_msg = payload + v2_block
    if len(pos_msg) % 4 != 0:
        pos_msg += b'\0' * (4 - (len(pos_msg) % 4))
    header_len = 32
    msg_len = header_len + len(pos_msg)
    header = create_msg_header(airplane.callsign, POS_DATA_ID, msg_len)
    packet = header + pos_msg
    try:
        sock.sendto(packet, (host, port))
        try:
            sock.settimeout(0.1)
            sock.recvfrom(4096)
        except socket.timeout:
            pass
        except Exception as e:
            print(f"[DEBUG] recvfrom error (can ignore): {e}")
    except (socket.gaierror, OSError) as e:
        print(f"[WARNING] send_fg_position: network error ({e}), will retry next time.")
        # Optionally, could re-create the socket here if needed
    except Exception as e:
        print(f"[ERROR] send_fg_position: unexpected error: {e}")

def geodetic_to_ecef(lat_deg, lon_deg, alt_m):
    """
    Convert geodetic coordinates to ECEF (Earth-Centered, Earth-Fixed).
    lat_deg, lon_deg in degrees, alt_m in meters
    Returns (x, y, z) in meters
    """
    # WGS-84 ellipsoid parameters
    a = 6378137.0  # semi-major axis
    e2 = 6.69437999014e-3  # first eccentricity squared
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    N = a / math.sqrt(1 - e2 * math.sin(lat)**2)
    x = (N + alt_m) * math.cos(lat) * math.cos(lon)
    y = (N + alt_m) * math.cos(lat) * math.sin(lon)
    z = (N * (1 - e2) + alt_m) * math.sin(lat)
    return (x, y, z)

def ecef_to_geodetic(x, y, z):
    """
    Convert ECEF (x, y, z) in meters to geodetic coordinates (lat, lon in degrees, alt in meters).
    """
    # WGS-84 ellipsoid parameters
    a = 6378137.0
    e2 = 6.69437999014e-3
    b = a * math.sqrt(1 - e2)
    ep = math.sqrt((a**2 - b**2) / b**2)
    p = math.sqrt(x**2 + y**2)
    th = math.atan2(a * z, b * p)
    lon = math.atan2(y, x)
    lat = math.atan2(z + ep**2 * b * math.sin(th)**3, p - e2 * a * math.cos(th)**3)
    N = a / math.sqrt(1 - e2 * math.sin(lat)**2)
    alt = p / math.cos(lat) - N
    lat_deg = math.degrees(lat)
    lon_deg = math.degrees(lon)
    return lat_deg, lon_deg, alt

def udp_listener(listen_port=5010, on_aimodel=None):
    oldata =''
    """
    Listen for UDP packets on the given port and process each packet with the on_aimodel callback.
    If on_aimodel is None, print the AIModel values.
    """
    import struct
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.bind(("", listen_port))
    while True:
        try:
            data, addr = listen_sock.recvfrom(4096)
            if data != oldata:
                aimodel = parse_udp_packet_to_aimodel(data)
                #print (aimodel)
                oldata = data  # Update oldata to the current packet
            if on_aimodel:
                on_aimodel(aimodel)
            else:
                print(f"[UDP Listener] AIModel: callsign={aimodel.callsign['value']} heading={aimodel.heading_deg['value']:.2f} gx={aimodel.gx['value']:.2f} gy={aimodel.gy['value']:.2f} gz={aimodel.gz['value']:.2f}")
        except Exception as e:
            print(f"[UDP Listener] Error: {e}")

def parse_udp_packet_to_aimodel(data):
    """
    Parse a FlightGear MP UDP packet and return an AIModel object with the decoded values.
    """
    import struct
    import math
    aimodel = AIModel()
    if len(data) >= 32:
        header_fmt = '!6I8s'
        header = struct.unpack(header_fmt, data[:32])
        magic, proto_ver, msg_id, msg_len, req_range, reply_port, callsign = header
        callsign = callsign.decode('ascii', errors='ignore').rstrip('\0')
        # Minimum size for full struct: 96+16+24+12+12+12+12+12 = 196 bytes after header
        if len(data) >= 32 + 96 + 2*8 + 3*8 + 3*4*5:
            offset = 32
            model = data[offset:offset+96].split(b'\0',1)[0].decode('ascii', errors='ignore')
            offset += 96
            time_val, lag = struct.unpack('!2d', data[offset:offset+16])
            offset += 16
            pos = struct.unpack('!3d', data[offset:offset+24])
            offset += 24
            orientation = struct.unpack('!3f', data[offset:offset+12])
            offset += 12
            linearVel = struct.unpack('!3f', data[offset:offset+12])
            offset += 12
            angularVel = struct.unpack('!3f', data[offset:offset+12])
            offset += 12
            linearAccel = struct.unpack('!3f', data[offset:offset+12])
            offset += 12
            angularAccel = struct.unpack('!3f', data[offset:offset+12])
            offset += 12
            # Fill AIModel fields (new format)
            aimodel.callsign = callsign
            aimodel.model_name = model
            aimodel.time = time_val
            aimodel.lag = lag
            aimodel.gx = pos[0]
            aimodel.gy = pos[1]
            aimodel.gz = pos[2]
            aimodel.orix = orientation[0]
            aimodel.oriy = orientation[1]
            aimodel.oriz = orientation[2]
            aimodel.linearVel = linearVel
            aimodel.angularVel = angularVel
            aimodel.linearAccel = linearAccel
            aimodel.angularAccel = angularAccel
            # Convert ECEF to geodetic and store in AIModel
            lat_deg, lon_deg, alt_m = ecef_to_geodetic(pos[0], pos[1], pos[2])
            aimodel.latitude_deg = lat_deg
            aimodel.longitude_deg = lon_deg
            aimodel.altitude_m = alt_m
            aimodel.altitude_ft = alt_m / 0.3048
            # Optionally: parse V2 property block for more fields
            # (not implemented here)
    return aimodel

def fg_angle_axis(heading_deg, pitch_deg, roll_deg, lat_deg, lon_deg):
    # Use degrees directly for clarity
    q_hpr = R.from_euler('ZYX', [heading_deg, pitch_deg, roll_deg], degrees=True)
    q_lat = R.from_euler('y', -(90 + lat_deg), degrees=True)
    q_lon = R.from_euler('z', -lon_deg, degrees=True)
    q_ned2ecef = q_lat * q_lon
    q = q_ned2ecef * q_hpr
    axis = q.as_rotvec()
    return float(axis[0]), float(axis[1]), float(axis[2])

def make_example_route(start_lat, start_lon, start_alt):
    """Create a simple closed route of 4 waypoints in a square pattern."""
    d_nm = 2.0  # 2 nautical miles between waypoints
    d_m = d_nm * 1852
    # 4 points: N, E, S, W of start
    waypoints = []
    for bearing_deg, alt_offset in zip([0, 90, 180, 270], [0, 200, 0, -200]):
        bearing_rad = math.radians(bearing_deg)
        lat0_rad = math.radians(start_lat)
        lon0_rad = math.radians(start_lon)
        lat_rad = math.asin(math.sin(lat0_rad) * math.cos(d_m / 6371000.0) +
                            math.cos(lat0_rad) * math.sin(d_m / 6371000.0) * math.cos(bearing_rad))
        lon_rad = lon0_rad + math.atan2(math.sin(bearing_rad) * math.sin(d_m / 6371000.0) * math.cos(lat0_rad),
                                        math.cos(d_m / 6371000.0) - math.sin(lat0_rad) * math.sin(lat_rad))
        waypoints.append({
            "lat": math.degrees(lat_rad),
            "lon": math.degrees(lon_rad),
            "alt": start_alt + alt_offset
        })
    return waypoints

# Helper to offset lat/lon by meters north/east
def offset_latlon(lat, lon, north_m, east_m):
    dlat = north_m / 111320.0
    dlon = east_m / (111320.0 * math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon

patterns=[
  {
    "phase": "approach",
    "patterns": [
      {
        "name": "lepp_ldw33",
        "waypoints": [
          {"lat": 42.76700595755307, "lon": -1.6661284078520953, "alt": 2500.0, "sequence": 0},
          {"lat": 42.732964, "lon": -1.646073, "alt": 2500.0, "sequence": 1},
          {"lat": 42.741205, "lon": -1.626102, "alt": 2500.0, "sequence": 2},
          {"lat": 42.76736475606018, "lon": -1.64442155733066, "alt": 1490.0, "sequence": 3}
        ]
      },
      {
        "name": "lepp_rdw33",
        "waypoints": [
          {"lat": 42.78136147319209, "lon": -1.6219439870806587, "alt": 2500.0, "sequence": 0},
          {"lat": 42.747857, "lon": -1.602964, "alt": 2500.0, "sequence": 1},
          {"lat": 42.741205, "lon": -1.626102, "alt": 2500.0, "sequence": 2},
          {"lat": 42.76736475606018, "lon": -1.64442155733066, "alt": 1490.0, "sequence": 3}
        ]
      },
      {
        "name": "lepp_ldw15",
        "waypoints": [
          {"lat": 42.78136147319209, "lon": -1.6219439870806587, "alt": 2500.0, "sequence": 0},
          {"lat": 42.80652051332688, "lon": -1.6481950935165997, "alt": 2500.0, "sequence": 1},
          {"lat": 42.790900, "lon": -1.661800, "alt": 2500.0, "sequence": 2},
          {"lat": 42.77706011288575, "lon": -1.651421279438418, "alt": 1490.0, "sequence": 3}
        ]
      },
      {
        "name": "lepp_rdw15",
        "waypoints": [
          {"lat": 42.76700595755307, "lon": -1.6661284078520953, "alt": 2500.0, "sequence": 0},
          {"lat": 42.784789, "lon": -1.677414, "alt": 2500.0, "sequence": 1},
          {"lat": 42.790900, "lon": -1.661800, "alt": 2500.0, "sequence": 2},
          {"lat": 42.77706011288575, "lon": -1.651421279438418, "alt": 1490.0, "sequence": 3}
        ]
      }
    ]
  },
  {
    "phase": "taxi",
    "patterns": [
      {
        "name": "lepp_taxiout_rwy33",
        "waypoints": [
          {"lat": 42.766835633044096, "lon": -1.6410385847781723, "alt": 1492.49, "sequence": 0},
          {"lat": 42.766482793815285, "lon": -1.6411238354501705, "alt": 1496.24, "sequence": 1},
          {"lat": 42.766294768506185, "lon": -1.6411236684145725, "alt": 1496.55, "sequence": 2},
          {"lat": 42.76567187189359, "lon": -1.6409635679158128, "alt": 1495.89, "sequence": 3},
          {"lat": 42.76533502455703, "lon": -1.6412251360014825, "alt": 1495.55, "sequence": 4},
          {"lat": 42.76519727263795, "lon": -1.6415294702142047, "alt": 1495.87, "sequence": 5},
          {"lat": 42.76450269735708, "lon": -1.642248929206552, "alt": 1493.45, "sequence": 6},
          {"lat": 42.76112702435747, "lon": -1.6398180245756173, "alt": 1502.20, "sequence": 7},
          {"lat": 42.76073992581595, "lon": -1.6390893976786445, "alt": 1499.64, "sequence": 8},
          {"lat": 42.76012970878455, "lon": -1.6388217595536763, "alt": 1489.24, "sequence": 9},
          {"lat": 42.76226250240739, "lon": -1.6406594648881032, "alt": 1496.50, "sequence": 10}
        ]
      },
      {
        "name": "lepp_taxiout_rwy15",
        "waypoints": [
          {"lat": 42.766835633044096, "lon": -1.6410385847781723, "alt": 1492.49, "sequence": 0},
          {"lat": 42.766482793815285, "lon": -1.6411238354501705, "alt": 1496.24, "sequence": 1},
          {"lat": 42.766294768506185, "lon": -1.6411236684145725, "alt": 1496.55, "sequence": 2},
          {"lat": 42.76567187189359, "lon": -1.6409635679158128, "alt": 1495.89, "sequence": 3},
          {"lat": 42.76533502455703, "lon": -1.6412251360014825, "alt": 1495.55, "sequence": 4},
          {"lat": 42.76519727263795, "lon": -1.6415294702142047, "alt": 1495.87, "sequence": 5},
          {"lat": 42.765100682087734, "lon": -1.6424115486111617, "alt": 1494.79, "sequence": 6},
          {"lat": 42.765602294262095, "lon": -1.6431021549987794, "alt": 1491.31, "sequence": 7},
          {"lat": 42.778660812861276, "lon": -1.652599087489504, "alt": 1468.14, "sequence": 8},
          {"lat": 42.7790878001637, "lon": -1.6526221823766498, "alt": 1470.64, "sequence": 9},
          {"lat": 42.77957241844156, "lon": -1.6527946909590827, "alt": 1467.48, "sequence": 10},
          {"lat": 42.77944595946831, "lon": -1.6531912841567031, "alt": 1463.97, "sequence": 11},
          {"lat": 42.77810963152101, "lon": -1.6522035691364472, "alt": 1465.99, "sequence": 12}
        ]
      }
    ]
  },
  {
    "phase": "takeoff",
    "patterns": [
      {
        "name": "lepp_takeoff_rwy33",
        "waypoints": [
          {"lat": 42.77713554401733, "lon": -1.651538430182954, "alt": 1471.05, "sequence": 0},
          {"lat": 42.77981962643002, "lon": -1.6534389001287242, "alt": 1970.64, "sequence": 1},
          {"lat": 42.79044288722373, "lon": -1.6609001102769063, "alt": 2200.64, "sequence": 2},
        ]
      },
      {
        "name": "lepp_takeoff_rwy15",
        "waypoints": [
          {"lat": 42.777003808654165, "lon": -1.6514074805556942, "alt": 1471.36, "sequence": 0},
          {"lat": 42.767274764120216, "lon": -1.6444154776873772, "alt": 1985, "sequence": 1},
          {"lat": 42.730406267596535, "lon": -1.6158071740787958, "alt": 2200.0, "sequence": 2},
        ]
      }
    ]
  },
  {
    "phase": "vapproach",
    "patterns": [
      {
        "name": "lepp_vacate_w",
        "waypoints": [
          { "lat": 42.741741813054034, "lon": -1.8632187684957007, "alt": 3500, "sequence": 0 },
        ]
      },
      {
        "name": "lepp_vacate_n",
        "waypoints": [
          { "lat": 42.94893187498391, "lon": -1.5398030581206072, "alt": 3500, "sequence": 0 },
        ]
      },
      {
        "name": "lepp_vacate_e",
        "waypoints": [
          { "lat": 42.800003450633476, "lon": -1.4661539300254585, "alt": 3500, "sequence": 0 },
        ]
      }
    ]
  }
]


def print_pattern_waypoints_google_links():
    print("\nPattern waypoints as Google Maps links:")
    for phase_obj in patterns:
        phase = phase_obj.get("phase", "?")
        for idx, pattern in enumerate(phase_obj.get("patterns", [])):
            pattern_name = pattern.get("name", f"Pattern {idx+1}")
            print(f"\nPattern {idx+1} (phase: {phase}, name: {pattern_name}):")
            for wp_idx, wp in enumerate(pattern.get("waypoints", [])):
                lat = wp["lat"]
                lon = wp["lon"]
                alt = wp.get("alt", "")
                link = f"https://www.google.com/maps?q={lat},{lon}"
                print(f"  WP{wp_idx+1}: {lat:.8f}, {lon:.8f}, alt={alt}  {link}")

# Debug: print Google Maps links for all patterns
if __name__ == "__main__":
    print_pattern_waypoints_google_links()

def generate_manoeuvre_waypoints(center_lat, center_lon, base_alt_ft, duration_sec=1200, update_frequency=0.1):
    """
    Generate a sequence of waypoints for a manoeuvre phase (mix of large, smooth 360° turns, S-turns, and stall exercises),
    lasting about duration_sec seconds, always above base_alt_ft.
    Each manoeuvre is smooth, with realistic attitude and altitude changes.
    """
    waypoints = []
    t = 0
    speed_kt = 120  # typical cruise
    speed_mps = speed_kt * 0.514444
    dt = update_frequency
    phase = "manoeuvre"
    lat = center_lat
    lon = center_lon
    alt = base_alt_ft
    heading = random.uniform(0, 360)
    pitch = 0.0
    roll = 0.0
    # Start at center
    waypoints.append({"lat": lat, "lon": lon, "alt": alt, "heading": heading, "pitch": pitch, "roll": roll, "phase": phase})
    while t < duration_sec:
        manoeuvre_type = random.choices([
            "circle", "sturn", "stall"
        ], weights=[0.5, 0.3, 0.2])[0]
        if manoeuvre_type == "circle":
            # Large, smooth 360° turn (coordinated turn)
            circle_time = random.uniform(180, 300)  # 3-5 min
            n_points = int(circle_time / dt)
            radius_nm = random.uniform(2.0, 3.5)  # larger radius
            radius_m = radius_nm * 1852
            turn_dir = random.choice([-1, 1])
            start_angle = random.uniform(0, 360)
            for i in range(n_points):
                frac = i / n_points
                angle = start_angle + turn_dir * 360 * frac
                angle_rad = math.radians(angle)
                dlat = (radius_m / 111320.0) * math.cos(angle_rad)
                dlon = (radius_m / (111320.0 * math.cos(math.radians(center_lat)))) * math.sin(angle_rad)
                # Smoothly vary altitude ±200ft
                alt_offset = 200 * math.sin(2 * math.pi * frac)
                alt_manoeuvre = max(base_alt_ft, alt + alt_offset)
                # Smooth roll for coordinated turn (max 25°)
                roll = 25.0 * turn_dir * math.sin(math.pi * frac)
                # Heading tangent to circle
                heading = (angle + 90 * turn_dir) % 360
                pitch = 2.0 * math.sin(2 * math.pi * frac)  # gentle pitch oscillation
                waypoints.append({
                    "lat": center_lat + dlat,
                    "lon": center_lon + dlon,
                    "alt": alt_manoeuvre,
                    "heading": heading,
                    "pitch": pitch,
                    "roll": roll,
                    "phase": phase
                })
                t += dt
                if t >= duration_sec:
                    break
            # Update center to end of circle
            lat = waypoints[-1]["lat"]
            lon = waypoints[-1]["lon"]
            alt = waypoints[-1]["alt"]
        elif manoeuvre_type == "sturn":
            # S-turns: two large, smooth opposite turns
            s_leg_time = random.uniform(60, 120)  # 1-2 min per S
            n_points = int(2 * s_leg_time / dt)
            s_radius_nm = random.uniform(1.5, 2.5)
            s_radius_m = s_radius_nm * 1852
            s_dir = random.choice([-1, 1])
            for i in range(n_points):
                frac = i / n_points
                # Sine wave for S-turn
                s_angle = 90 * s_dir * math.sin(2 * math.pi * frac)
                heading = (heading + s_angle * dt) % 360
                # Offset from centerline
                offset = s_radius_m * math.sin(2 * math.pi * frac)
                dlat = (offset / 111320.0) * math.cos(math.radians(heading))
                dlon = (offset / (111320.0 * math.cos(math.radians(lat)))) * math.sin(math.radians(heading))
                # Smooth roll for S-turn (max 20°)
                roll = 20.0 * math.sin(2 * math.pi * frac)
                # Gentle pitch oscillation
                pitch = 1.5 * math.sin(4 * math.pi * frac)
                # Smooth altitude change ±150ft
                alt_offset = 150 * math.sin(2 * math.pi * frac)
                alt_manoeuvre = max(base_alt_ft, alt + alt_offset)
                waypoints.append({
                    "lat": lat + dlat,
                    "lon": lon + dlon,
                    "alt": alt_manoeuvre,
                    "heading": heading,
                    "pitch": pitch,
                    "roll": roll,
                    "phase": phase
                })
                t += dt
                if t >= duration_sec:
                    break
            # Update position
            lat = waypoints[-1]["lat"]
            lon = waypoints[-1]["lon"]
            alt = waypoints[-1]["alt"]
        else:
            # Stall exercise: slow, gentle climb, then nose up, then recovery
            climb_time = random.uniform(30, 60)
            stall_time = random.uniform(10, 20)
            recover_time = random.uniform(20, 40)
            n_climb = int(climb_time / dt)
            n_stall = int(stall_time / dt)
            n_recover = int(recover_time / dt)
            # Climb
            for i in range(n_climb):
                frac = i / n_climb
                pitch = 8.0 + 2.0 * math.sin(math.pi * frac)
                roll = 0.0
                alt_manoeuvre = alt + 300 * frac
                waypoints.append({
                    "lat": lat,
                    "lon": lon,
                    "alt": alt_manoeuvre,
                    "heading": heading,
                    "pitch": pitch,
                    "roll": roll,
                    "phase": phase
                })
                t += dt
                if t >= duration_sec:
                    break
            # Stall (nose up, low speed)
            for i in range(n_stall):
                frac = i / n_stall
                pitch = 15.0 - 10.0 * frac  # nose up, then dropping
                roll = 0.0
                alt_manoeuvre = alt + 300 - 50 * frac
                waypoints.append({
                    "lat": lat,
                    "lon": lon,
                    "alt": alt_manoeuvre,
                    "heading": heading,
                    "pitch": pitch,
                    "roll": roll,
                    "phase": phase
                })
                t += dt
                if t >= duration_sec:
                    break
            # Recovery (nose down, then level)
            for i in range(n_recover):
                frac = i / n_recover
                pitch = 5.0 - 5.0 * frac
                roll = 0.0
                alt_manoeuvre = alt + 250 - 200 * frac
                waypoints.append({
                    "lat": lat,
                    "lon": lon,
                    "alt": alt_manoeuvre,
                    "heading": heading,
                    "pitch": pitch,
                    "roll": roll,
                    "phase": phase
                })
                t += dt
                if t >= duration_sec:
                    break
            # End of stall, update altitude
            alt = waypoints[-1]["alt"]
    return waypoints

