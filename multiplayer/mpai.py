import socket
import time
import sys
import math
import threading
import random
import string
from collections import defaultdict
from mp import AIModel, send_fg_position, udp_listener, patterns, fg_angle_axis, geodetic_to_ecef, generate_manoeuvre_waypoints
import re
import srtm

HOST = "mpserver01.flightgear.org"  # FlightGear MP server IP
PORT = 5000           # FlightGear MP server port
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
update_frequency = 0.1  # 10 Hz for demo, must be > 0 for movement
LEPP_LAT = 42.7700
LEPP_LON = -1.6463
METERS_PER_DEG_LAT = 111320.0
METERS_PER_DEG_LON_REF = 111320.0 * math.cos(math.radians(LEPP_LAT))

fgairplane = AIModel()
fgairplane_lock = threading.Lock()

def update_fgairplane(new_aimodel):
    with fgairplane_lock:
        fgairplane.__dict__.update(new_aimodel.__dict__)

listener_thread = threading.Thread(target=udp_listener, args=(5002, update_fgairplane), daemon=True)
listener_thread.start()

# There may be multiple 'approach' patterns, so collect all
approach_patterns = [p for p in patterns if p["phase"].lower() == "approach"]

pattern_phases = [p["phase"].lower() for p in patterns]
if not (any(n == "taxi" for n in pattern_phases) and any(n == "takeoff" for n in pattern_phases) and any(n == "vapproach" for n in pattern_phases) and any(n == "approach" for n in pattern_phases)):
    raise ValueError("patterns variable must contain at least one 'taxi', 'takeoff', 'vapproach', and 'approach' phase")

def calc_heading(latA, lonA, latB, lonB,doi=False):
    lat0r = math.radians(latA)
    lon0r = math.radians(lonA)
    lat1r = math.radians(latB)
    lon1r = math.radians(lonB)
    y = math.sin(lon1r - lon0r) * math.cos(lat1r)
    x = math.cos(lat0r) * math.sin(lat1r) - math.sin(lat0r) * math.cos(lat1r) * math.cos(lon1r - lon0r)
    bearing_rad = math.atan2(y, x)
    heading = (math.degrees(bearing_rad) + 360) % 360
    if doi: 
        print(f"[HEADING-CALC] from=({latA:.6f},{lonA:.6f}) to=({latB:.6f},{lonB:.6f}) heading={heading:.2f}")
    return heading

def interpolate_route(waypoints, phase, rwy=None, airspeed_kt=15.0, initial_heading=None, start_airspeed_kt=None, end_airspeed_kt=None, pattern_name=None):
    # Interpolate points between each pair of waypoints based on ground speed and update_frequency
    points = []
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000.0  # meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    # Add initial waiting points (only for the first phase and first segment)
    if len(waypoints) > 0 and phase == "taxi":
        wait_time = 10.0  # seconds
        n_wait = int(wait_time / update_frequency)
        wp = waypoints[0]
        lat = wp["lat"]
        lon = wp["lon"]
        alt = wp["alt"] * 0.3048
        from mp import geodetic_to_ecef
        posx, posy, posz = geodetic_to_ecef(lat, lon, alt)
        heading = initial_heading if initial_heading is not None else 155.0
        pitch = 0.0
        bank = 0.0
        orix, oriy, oriz = fg_angle_axis(heading, pitch, bank, lat, lon)
        for i in range(n_wait):
            pt = {"lat": lat, "lon": lon, "alt": wp["alt"], "phase": "startup", "airspeed_kt": 0.0, "heading": heading,
                  "pitch": pitch, "bank": bank, "orix": orix, "oriy": oriy, "oriz": oriz, "sequence": wp.get("sequence", 0),
                  "posx": posx, "posy": posy, "posz": posz, "rpm": 1200}
            if rwy is not None:
                pt["rwy"] = rwy
            points.append(pt)
    for idx, wp in enumerate(waypoints):
        for key in ("lat", "lon", "alt"):
            if wp.get(key) is None:
                raise ValueError(f"Waypoint {idx} in phase '{phase}' (rwy={rwy}) has None for '{key}': {wp}")
        # Calculate ECEF position for each point
        lat = wp["lat"]
        lon = wp["lon"]
        alt = wp["alt"] * 0.3048  # convert ft to meters
        from mp import geodetic_to_ecef
        posx, posy, posz = geodetic_to_ecef(lat, lon, alt)
        if idx == 0:
            heading = initial_heading if initial_heading is not None else 155.0
            # Calculate pitch and bank
            pitch = 0.0
            bank = 0.0
            if phase != "taxi" and idx < len(waypoints) - 1:
                # Estimate pitch from climb/descent angle
                next_wp = waypoints[idx + 1]
                horiz_dist = haversine(wp["lat"], wp["lon"], next_wp["lat"], next_wp["lon"])
                vert_dist = next_wp["alt"] - wp["alt"]
                pitch = math.degrees(math.atan2(vert_dist, horiz_dist))
                # Estimate bank from heading change
                heading_next = calc_heading(wp["lat"], wp["lon"], next_wp["lat"], next_wp["lon"])
                delta_heading = (heading_next - heading + 540) % 360 - 180
                if phase == "takeoff":
                    bank = max(-30, min(30, delta_heading * 0.5))
                else:
                    bank = max(-30, min(30, delta_heading * 0.5))
            orix, oriy, oriz = fg_angle_axis(heading, pitch, bank, wp["lat"], wp["lon"])
            pt = {"lat": lat, "lon": lon, "alt": wp["alt"], "phase": phase, "airspeed_kt": airspeed_kt, "heading": heading,
                  "pitch": pitch, "bank": bank, "orix": orix, "oriy": oriy, "oriz": oriz, "sequence": wp.get("sequence", idx),
                  "posx": posx, "posy": posy, "posz": posz}
            # Set rpm for first point
            if phase == "taxi":
                pt["rpm"] = 1200
            elif phase == "takeoff":
                pt["rpm"] = 2800
            elif phase in ("vapproach", "approach"):
                pt["rpm"] = 2300
            else:
                pt["rpm"] = 1200
            if rwy is not None:
                pt["rwy"] = rwy
            points.append(pt)
        else:
            prev_wp = waypoints[idx - 1]
            dist = haversine(prev_wp["lat"], prev_wp["lon"], wp["lat"], wp["lon"])
            # Determine airspeed for this segment
            if phase == "takeoff" and start_airspeed_kt is not None and end_airspeed_kt is not None:
                seg_start_kt = start_airspeed_kt
                seg_end_kt = end_airspeed_kt
            else:
                seg_start_kt = airspeed_kt
                seg_end_kt = airspeed_kt
            # Use average for GS
            avg_kt = (seg_start_kt + seg_end_kt) / 2.0
            gs = avg_kt * 0.514444
            # Calculate time to travel this segment
            time_to_travel = dist / gs if gs > 0 else 1.0
            n_points = max(1, int(time_to_travel / update_frequency))
            # For taxi, precompute heading change for smooth, constant-rate turn
            if phase == "taxi":
                heading_start = calc_heading(prev_wp["lat"], prev_wp["lon"], wp["lat"], wp["lon"])
                if idx < len(waypoints) - 1:
                    next_wp = waypoints[idx + 1]
                    heading_end = calc_heading(wp["lat"], wp["lon"], next_wp["lat"], next_wp["lon"])
                else:
                    heading_end = heading_start
                delta_heading = ((heading_end - heading_start + 540) % 360) - 180
            for i in range(1, n_points + 1):
                frac = i / (n_points + 1)
                lat = prev_wp["lat"] + frac * (wp["lat"] - prev_wp["lat"])
                lon = prev_wp["lon"] + frac * (wp["lon"] - prev_wp["lon"])
                alt = prev_wp["alt"] + frac * (wp["alt"] - prev_wp["alt"])
                # Calculate ECEF for interpolated point
                alt_m = alt * 0.3048
                posx, posy, posz = geodetic_to_ecef(lat, lon, alt_m)
                if phase == "taxi":
                    # Heading is always direction of movement for taxi phase
                    interp_heading = calc_heading(prev_wp["lat"], prev_wp["lon"], lat, lon)
                else:
                    interp_heading = calc_heading(prev_wp["lat"], prev_wp["lon"], lat, lon)
                # Calculate pitch and bank for interpolated points
                pitch = 0.0
                bank = 0.0
                if phase == "takeoff":
                    heading_prev = calc_heading(prev_wp["lat"], prev_wp["lon"], lat, lon)
                    heading_next = calc_heading(lat, lon, wp["lat"], wp["lon"])
                    delta_h = (heading_next - heading_prev + 540) % 360 - 180
                    bank = max(-30, min(30, delta_h * 0.5))
                    horiz_dist = haversine(prev_wp["lat"], prev_wp["lon"], lat, lon)
                    vert_dist = alt - prev_wp["alt"]
                    pitch = math.degrees(math.atan2(vert_dist, horiz_dist))
                elif phase != "taxi":
                    horiz_dist = haversine(prev_wp["lat"], prev_wp["lon"], lat, lon)
                    vert_dist = alt - prev_wp["alt"]
                    pitch = math.degrees(math.atan2(vert_dist, horiz_dist))
                    heading_prev = calc_heading(prev_wp["lat"], prev_wp["lon"], lat, lon)
                    heading_next = calc_heading(lat, lon, wp["lat"], wp["lon"])
                    delta_h = (heading_next - heading_prev + 540) % 360 - 180
                    bank = max(-30, min(30, delta_h * 0.5))
                # Interpolate airspeed for takeoff phase
                if phase == "takeoff" and start_airspeed_kt is not None and end_airspeed_kt is not None:
                    airspeed = seg_start_kt + frac * (seg_end_kt - seg_start_kt)
                else:
                    airspeed = airspeed_kt
                # Set rpm for interpolated points
                if phase == "taxi":
                    rpm = 1200
                elif phase == "takeoff":
                    rpm = 2800
                elif phase in ("vapproach", "approach"):
                    # Determine climb, cruise, or descent by pitch
                    if pitch > 2.0:
                        rpm = 2800  # climbing
                    elif pitch < -2.0:
                        rpm = 1800  # descending
                    else:
                        rpm = 2300  # cruise
                else:
                    rpm = 1200
                orix, oriy, oriz = fg_angle_axis(interp_heading, pitch, bank, lat, lon)
                pt = {"lat": lat, "lon": lon, "alt": alt, "phase": phase, "airspeed_kt": airspeed, "heading": interp_heading,
                      "pitch": pitch, "bank": bank, "orix": orix, "oriy": oriy, "oriz": oriz, "sequence": wp.get("sequence", idx),
                      "posx": posx, "posy": posy, "posz": posz, "rpm": rpm}
                if rwy is not None:
                    pt["rwy"] = rwy
                points.append(pt)
            # Add the actual waypoint
            pitch = 0.0
            bank = 0.0
            if phase == "takeoff" and idx < len(waypoints) - 1:
                next_wp = waypoints[idx + 1]
                heading = calc_heading(prev_wp["lat"], prev_wp["lon"], wp["lat"], wp["lon"])
                heading_next = calc_heading(wp["lat"], wp["lon"], next_wp["lat"], next_wp["lon"])
                delta_h = (heading_next - heading + 540) % 360 - 180
                bank = max(-30, min(30, delta_h * 0.5))
                horiz_dist = haversine(wp["lat"], wp["lon"], next_wp["lat"], next_wp["lon"])
                vert_dist = next_wp["alt"] - wp["alt"]
                pitch = math.degrees(math.atan2(vert_dist, horiz_dist))
                heading_at_wp = heading_next
            elif phase == "takeoff":
                heading = calc_heading(waypoints[idx - 1]["lat"], waypoints[idx - 1]["lon"], wp["lat"], wp["lon"])
                heading_at_wp = heading
            elif phase == "taxi" and idx < len(waypoints) - 1:
                heading_at_wp = calc_heading(wp["lat"], wp["lon"], waypoints[idx + 1]["lat"], waypoints[idx + 1]["lon"])
            elif phase == "taxi":
                heading_at_wp = calc_heading(waypoints[idx - 1]["lat"], waypoints[idx - 1]["lon"], wp["lat"], wp["lon"])
            else:
                heading_at_wp = heading
            orix, oriy, oriz = fg_angle_axis(heading_at_wp, pitch, bank, wp["lat"], wp["lon"])
            # Calculate ECEF for actual waypoint
            alt_m = wp["alt"] * 0.3048
            posx, posy, posz = geodetic_to_ecef(wp["lat"], wp["lon"], alt_m)
            pt = {"lat": wp["lat"], "lon": wp["lon"], "alt": wp["alt"], "phase": phase, "airspeed_kt": seg_end_kt, "heading": heading_at_wp,
                  "pitch": pitch, "bank": bank, "orix": orix, "oriy": oriy, "oriz": oriz, "sequence": wp.get("sequence", idx),
                  "posx": posx, "posy": posy, "posz": posz}
            # Set rpm for actual waypoint
            if phase == "taxi":
                pt["rpm"] = 1200
            elif phase == "takeoff":
                pt["rpm"] = 2800
            elif phase in ("vapproach", "approach"):
                if pitch > 2.0:
                    pt["rpm"] = 2800
                elif pitch < -2.0:
                    pt["rpm"] = 1800
                else:
                    pt["rpm"] = 2300
            else:
                pt["rpm"] = 1200
            # Set rwy attribute for taxi, approach, and takeoff phases
            if phase in ("taxi", "takeoff", "approach"):
                rwy_val = None
                if rwy is not None:
                    rwy_val = rwy
                else:
                    import re
                    # Use pattern_name for extraction
                    pat_name = pattern_name or ''
                    match = re.search(r'rwy(\d+)', pat_name)
                    if match:
                        rwy_val = int(match.group(1))
                if rwy_val is not None:
                    pt["rwy"] = rwy_val
            points.append(pt)
    return points

def build_full_route():
    phase_patterns = defaultdict(list)
    for phase_obj in patterns:
        phase = phase_obj["phase"].lower()
        for pattern in phase_obj["patterns"]:
            phase_patterns[phase].append(pattern)
    taxi_pattern = random.choice(phase_patterns["taxi"])
    # Extract runway from taxi pattern name
    import re
    taxi_pattern_name = taxi_pattern.get("name", "")
    taxi_rwy = None
    match = re.search(r'rwy(\d+)', taxi_pattern_name)
    if match:
        taxi_rwy = int(match.group(1))
    takeoff_matches = [p for p in phase_patterns["takeoff"] if taxi_rwy is not None and str(taxi_rwy) in p.get("name", "")]
    if not takeoff_matches:
        raise ValueError(f"No takeoff pattern matches taxi pattern rwy: {taxi_rwy}")
    takeoff_pattern = random.choice(takeoff_matches)
    vapproach_pattern = random.choice(phase_patterns["vapproach"])
    approach_pattern = random.choice(phase_patterns["approach"])
    route = []
    # Taxi phase
    taxi_points = interpolate_route(
        taxi_pattern["waypoints"], "taxi", rwy=taxi_rwy, airspeed_kt=20.0, initial_heading=155.0, pattern_name=taxi_pattern.get("name")
    )
    route += taxi_points
    # Takeoff phase: start at last taxi point, accelerate to cruise
    takeoff_start_speed = taxi_points[-1]["airspeed_kt"]
    takeoff_target_speed = random.uniform(80, 120)
    takeoff_wps = [dict(taxi_points[-1]), *takeoff_pattern["waypoints"]]
    takeoff_points = interpolate_route(
        takeoff_wps, "takeoff", rwy=taxi_rwy, airspeed_kt=takeoff_target_speed, initial_heading=taxi_points[-1]["heading"],
        start_airspeed_kt=takeoff_start_speed, end_airspeed_kt=takeoff_target_speed, pattern_name=takeoff_pattern.get("name")
    )
    takeoff_points = takeoff_points[1:]
    route += takeoff_points
    # vapproach entry phase: go to vapproach point before manoeuvre
    vapproach_first_wp = vapproach_pattern["waypoints"][0]
    vapproach_entry_points = interpolate_route(
        [dict(route[-1]), vapproach_first_wp], "vapproach", rwy=None, airspeed_kt=takeoff_target_speed, initial_heading=route[-1]["heading"], pattern_name=vapproach_pattern.get("name")
    )
    vapproach_entry_points = vapproach_entry_points[1:]
    route += vapproach_entry_points
    # Manoeuvre phase: generate random manoeuvres near vapproach point
    manoeuvre_center_lat = vapproach_first_wp["lat"]
    manoeuvre_center_lon = vapproach_first_wp["lon"]
    manoeuvre_base_alt = max(3500, vapproach_first_wp["alt"])
    from mp import generate_manoeuvre_waypoints
    manoeuvre_points = generate_manoeuvre_waypoints(
        manoeuvre_center_lat, manoeuvre_center_lon, manoeuvre_base_alt,
        duration_sec=600,  # Halved from 1200 to 600 seconds
        update_frequency=update_frequency
    )
    # Ensure at least 500ft AGL for each manoeuvre point
    for pt in manoeuvre_points:
        ground_ft = get_ground_elevation(pt["lat"], pt["lon"])
        min_alt_ft = ground_ft + 500
        if pt["alt"] < min_alt_ft:
            pt["alt"] = min_alt_ft

    # Interpolate for smoothness
    manoeuvre_points = interpolate_route(manoeuvre_points, "manoeuvre", airspeed_kt=110.0, initial_heading=route[-1]["heading"])
    # Ensure at least 500ft AGL for each interpolated manoeuvre point
    for pt in manoeuvre_points:
        ground_ft = get_ground_elevation(pt["lat"], pt["lon"])
        min_alt_ft = ground_ft + 500
        if pt["alt"] < min_alt_ft:
            pt["alt"] = min_alt_ft
    route += manoeuvre_points

    # vapproach exit phase: return to vapproach point after manoeuvre
    vapproach_exit_points = interpolate_route(
        [dict(route[-1]), vapproach_first_wp], "vapproach", rwy=None, airspeed_kt=takeoff_target_speed,
        initial_heading=route[-1]["heading"], pattern_name=vapproach_pattern.get("name")
    )
    # Ensure at least 500ft AGL for each vapproach exit point
    for pt in vapproach_exit_points:
        ground_ft = get_ground_elevation(pt["lat"], pt["lon"])
        min_alt_ft = ground_ft + 500
        if pt["alt"] < min_alt_ft:
            pt["alt"] = min_alt_ft

    # Only skip the first point if there are at least two
    if len(vapproach_exit_points) > 1:
        vapproach_exit_points = vapproach_exit_points[1:]
    route += vapproach_exit_points

    # approach phase: start at vapproach point
    approach_wps = [dict(route[-1]), *approach_pattern["waypoints"]]
    approach_points = interpolate_route(
        approach_wps, "approach", rwy=taxi_rwy, airspeed_kt=takeoff_target_speed, initial_heading=route[-1]["heading"], pattern_name=approach_pattern.get("name")
    )
    approach_points = approach_points[1:]
    route += approach_points
    return route

num_planes = 10
planes = []
availmodels = [
    "AI/Aircraft/Arup-S2/Models/arup-s2-ai.xml",
    "AI/Aircraft/Beechcraft-Staggerwing/Models/model17-ai.xml",
    "AI/Aircraft/bf109/Models/bf109g-model.xml",
    "AI/Aircraft/c172/c-fgfs.xml",
    "AI/Aircraft/c172/c-fuhq.xml",
    "AI/Aircraft/c172/csna.xml",
    "AI/Aircraft/c172/ei-mcf.xml",
    "AI/Aircraft/c172/g-boix.xml",
    "AI/Aircraft/c172/g-fire.xml",
    "AI/Aircraft/c172/n4456r.xml",
    "AI/Aircraft/c172/n737bq.xml",
    "AI/Aircraft/c172/news.xml",
    "AI/Aircraft/c172/ok-ekr.xml",
    "AI/Aircraft/c172/ph-gys.xml",
    "AI/Aircraft/c172/tf-sex.xml",
    "AI/Aircraft/c182/Models/c182-ai.xml",
    "AI/Aircraft/c182/Models/c182-dpm.xml",
    "AI/Aircraft/c182rg/Models/c182rg-ai.xml",
    "AI/Aircraft/c182rg/Models/c182rg-dpm.xml",
    "AI/Aircraft/Cessna-421-Golden-Eagle/Models/c421-ai.xml",
    "AI/Aircraft/Cessna208Caravan/Models/Cessna208-ai.xml",
    "AI/Aircraft/Cessna337/Models/Cessna337-EC-ISDai.xml",
    "AI/Aircraft/Cessna337/Models/Cessna337-N53472ai.xml",
    "AI/Aircraft/Cessna337/Models/Cessna337-N6276Fai.xml",
    "AI/Aircraft/Cessna337/Models/Cessna337-VH-SBZai.xml",
    "AI/Aircraft/Cessna337/Models/Cessna337-VH-WWCai.xml",
    "AI/Aircraft/cri-cri/Models/MC-15-ai.xml",
    "AI/Aircraft/Cub/Models/Cub-ai.xml",
    "AI/Aircraft/DR400/Models/dr400-ai.xml",
    "AI/Aircraft/Dragonfly/Models/Banner.xml",
    "AI/Aircraft/Dragonfly/Models/Dragonfly-ai.xml",
    "AI/Aircraft/Dromader/Models/M18B_Dromader-ai.xml",
    "AI/Aircraft/Dromader/Models/M18B_DromaderR-ai.xml",
    "AI/Aircraft/ercoupe/Models/ercoupe-ai.xml",
    "AI/Aircraft/FK9MK2/Models/fk9mk2-ai.xml",
    "AI/Aircraft/Fokker-S-11/Models/s11-ai.xml",
    "AI/Aircraft/G-164/Models/G-164A-ai.xml",
    "AI/Aircraft/Gee-Bee/Models/geebee-ai.xml",
    "AI/Aircraft/pa-28/pa-28-d-emlh.xml",
    "AI/Aircraft/pa-28/pa-28-ec-jma.xml",
    "AI/Aircraft/pa-28/pa-28-g-bprn.xml",
    "AI/Aircraft/pa-28/pa-28-g-cbal.xml",
    "AI/Aircraft/pa-28/pa-28-g-egll.xml",
    "AI/Aircraft/pa-28/pa-28-g-nina.xml",
    "AI/Aircraft/pa-28/pa-28-g-warh.xml",
    "AI/Aircraft/pa-28/pa-28-hb-png.xml",
    "AI/Aircraft/pa-28/pa-28-main.xml",
    "AI/Aircraft/pa-28/pa-28-ph-edd.xml",
    "AI/Aircraft/Spitfire/Models/spitfire_model.xml"
]
def random_callsign():
    return "EC-" + ''.join(random.choices(string.ascii_uppercase, k=3))

plane_configs = []
for i in range(num_planes):
    cs = 'EC-JFY'
    while cs =='EC-JFY' or cs == 'EC-LNI':
        cs = random_callsign()
    plane_configs.append({
        "callsign": random_callsign(),
        "model_name": random.choice(availmodels)
    })

active_plane_idx = 0

def insert_next_plane(idx=None):
    global active_plane_idx
    # Only allow up to num_planes at a time
    if len(planes) >= num_planes:
        print(f"\033[95m[DEBUG] Maximum number of planes ({num_planes}) reached, not inserting new plane.\033[0m")
        return
    # Use a new config each time, or recycle if you want infinite
    cfg = {
        "callsign": random_callsign(),
        "model_name": random.choice(availmodels)
    }
    airplane = AIModel()
    airplane.callsign = cfg["callsign"]
    airplane.model_name = cfg["model_name"]
    airplane.time = time.time()
    airplane.lag = 0.1
    airplane.linearVel = (0.0, 0.0, 0.0)
    airplane.angularVel = (0.0, 0.0, 0.0)
    airplane.linearAccel = (0.0, 0.0, 0.0)
    airplane.angularAccel = (0.0, 0.0, 0.0)
    airplane.route = build_full_route()
    airplane.route_name = f"{airplane.callsign}_route"
    airplane.current_wp_idx = 0
    airplane.route_idx = 0
    airplane.latitude_deg = airplane.route[0]["lat"]
    airplane.longitude_deg = airplane.route[0]["lon"]
    airplane.altitude_ft = airplane.route[0]["alt"]
    airplane.airspeed_kt = random.uniform(15, 25)
    airplane.phase = airplane.route[0]['phase']
    airplane.prev_phase = None
    if idx is None:
        planes.append(airplane)
        print(f"\033[94m[DEBUG] Inserted new plane {airplane.callsign} ({airplane.model_name}) at END (len={len(planes)})\033[0m")
    else:
        planes.insert(idx, airplane)
        print(f"\033[94m[DEBUG] Inserted new plane {airplane.callsign} ({airplane.model_name}) at index {idx} (len={len(planes)})\033[0m")
    active_plane_idx += 1

def update_airplane_position(airplane):
    if not hasattr(airplane, 'route') or not airplane.route:
        return
    if not hasattr(airplane, 'route_idx'):
        airplane.route_idx = 0
    prev_phase = getattr(airplane, 'phase', None)
    prev_wp_idx = getattr(airplane, 'route_idx', 0)
    if airplane.route_idx < len(airplane.route) - 1:
        airplane.route_idx += 1
        pt = airplane.route[airplane.route_idx]
    else:
        pt = airplane.route[airplane.route_idx]
    # Remove all waypoints before the current one to save memory
    if airplane.route_idx > 0:
        airplane.route = airplane.route[airplane.route_idx:]
        airplane.route_idx = 0
        pt = airplane.route[0]
    airplane.latitude_deg = pt['lat']
    airplane.longitude_deg = pt['lon']
    airplane.altitude_ft = pt['alt']
    airplane.altitude_m = pt['alt'] * 0.3048
    airplane.phase = pt.get('phase', getattr(airplane, 'phase', None))
    airplane.airspeed_kt = pt.get('airspeed_kt', getattr(airplane, 'airspeed_kt', 0.0))
    airplane.heading_deg = pt['heading']
    airplane.orix = pt['orix']
    airplane.oriy = pt['oriy']
    airplane.oriz = pt['oriz']
    airplane.posx = pt.get('posx', None)
    airplane.posy = pt.get('posy', None)
    airplane.posz = pt.get('posz', None)
    airplane.rpm = pt.get('rpm', 0.0)  # Set rpm from waypoint if available
    # Dynamic chat logic
    chat = ""
    callsign = getattr(airplane, 'callsign', 'N/A')
    rwy = pt.get('rwy', None)
    # Detect phase transitions
    if prev_phase != airplane.phase:
        if airplane.phase == 'taxi' and rwy:
            chat = f"Pamplona tower {callsign} taxi to runway {rwy}"
        elif airplane.phase == 'takeoff' and rwy:
            chat = f"Pamplona tower {callsign} taking off from runway {rwy}"
        elif airplane.phase == 'vapproach':
            # Find reporting point (first waypoint in vapproach pattern after transition)
            reporting_point = ''
            if hasattr(airplane, 'route') and airplane.route_idx < len(airplane.route):
                # Try to get a name or sequence for the reporting point
                rp_pt = airplane.route[airplane.route_idx]
                reporting_point = rp_pt.get('name') or str(rp_pt.get('sequence', ''))
            chat = f"Pamplona tower {callsign} at {int(airplane.altitude_ft)} heading towards reporting point {reporting_point}"
    # Reporting point message: when reaching the last vapproach point (first approach point)
    if airplane.phase == 'approach' and prev_phase == 'vapproach':
        # This is the first approach point, so previous point is the reporting point
        reporting_point = ''
        if hasattr(airplane, 'route') and airplane.route_idx > 0:
            rp_pt = airplane.route[airplane.route_idx - 1]
            reporting_point = rp_pt.get('name') or str(rp_pt.get('sequence', ''))
            chat = f"Pamplona tower {callsign} over {reporting_point} altitude {int(airplane.altitude_ft)} heading {int(airplane.heading_deg)}"
    airplane.chat = chat
    # Debug: print phase transitions
    if prev_phase != airplane.phase:
        now_str = time.strftime("%H:%M:%S")
        if prev_phase == 'manoeuvre' and airplane.phase == 'vapproach':
            print(f"\033[91m[{now_str}] [DEBUG] {getattr(airplane, 'callsign', 'N/A')} phase transition: {prev_phase} -> {airplane.phase} (route_idx={airplane.route_idx})\033[0m")
        elif prev_phase == 'vapproach' and airplane.phase == 'approach':
            print(f"\033[92m[{now_str}] [DEBUG] {getattr(airplane, 'callsign', 'N/A')} phase transition: {prev_phase} -> {airplane.phase} (route_idx={airplane.route_idx})\033[0m")
        else:
            print(f"[{now_str}] [DEBUG] {getattr(airplane, 'callsign', 'N/A')} phase transition: {prev_phase}  -> {airplane.phase} (route_idx={airplane.route_idx})")

# Initialize SRTM data
srtm_data = srtm.get_data()

def get_ground_elevation(lat, lon):
    """Returns ground elevation in feet at the given lat/lon, or 0 if unavailable."""
    elev = srtm_data.get_elevation(lat, lon)
    if elev is None:
        return 0.0
    return elev * 3.28084  # meters to feet

if __name__ == "__main__":
    # For testing: generate a route (no export)
    test_route = build_full_route()

# Main simulation loop

t = 0
try:
    insert_next_plane()  # Start with one plane
    while True:
        i = 0
        while i < len(planes):
            airplane = planes[i]
            prev_phase = getattr(airplane, 'prev_phase', None)
            current_phase = getattr(airplane, 'phase', None)
            update_airplane_position(airplane)
            send_fg_position(airplane, HOST, PORT)
            # Insert new plane only once when entering takeoff phase
            if prev_phase != 'takeoff' and airplane.phase == 'takeoff' and not getattr(airplane, '_inserted_next', False):
                threading.Thread(target=insert_next_plane).start()
                airplane._inserted_next = True
            # Remove plane if it has finished its route and is in 'approach'
            if airplane.phase == 'approach' and airplane.route_idx >= len(airplane.route) - 1:
                duration = time.time() - getattr(airplane, 'time', time.time())
                mins, secs = divmod(int(duration), 60)
                print(f"\033[93m[DEBUG] Plane {airplane.callsign} completed flight in {mins}m {secs}s\033[0m")
                planes.remove(airplane)
                insert_next_plane(idx=i)  # Insert at the same index
                continue
            # Update prev_phase for next iteration
            airplane.prev_phase = airplane.phase
            i += 1
        t += update_frequency
        time.sleep(update_frequency)
except KeyboardInterrupt:
    print("[INFO] Simulation stopped by user.")
