import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Circle
import socket
import threading
import time
import math
import os
import sys
from collections import defaultdict
import elevation
import rasterio
import numpy as np
import matplotlib.colors as mcolors
import srtm
import requests

SERVER = '217.78.131.42'
PORT_TCP_ADMIN = 5001

SHOW_ELEVATION_BLOCKS = True  # Set to False to disable elevation blocks
SHOW_WEATHER_BLOCKS = False  # Set to False to disable weather overlay

DEBUG = True  # Set to False to disable debug output

class RadarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FlightGear Radar Display")
        self.root.geometry("1024x600")
        self.root.resizable(True, True)
        try:
            self.root.attributes('-topmost', False)
        except tk.TclError:
            pass

        self.tracked_callsign = None
        self.current_aircraft_index = 0
        self.tracked_zoom_range = 5
        self.default_radar_range = 10
        self.headless_mode = self.detect_headless_mode()

        self.preferred_callsign = "EC-LNI"
        self.auto_track_attempted = False
        self.ec_lni_auto_tracked = False
        self.user_switched_tracking = False

        self.aircraft_data = {}
        self.aircraft_history = defaultdict(list)
        self.last_update = time.time()
        self.is_running = False

        self.center_lat = 50.0
        self.center_lon = 10.0
        self.radar_range = self.default_radar_range

        self.srtm_data = srtm.get_data()  # <-- Move this up!

        self.weather_cache = {}  # (lat_rounded, lon_rounded) -> (timestamp, precipitation)
        self.weather_cache_minutes = 10  # Cache duration in minutes

        if DEBUG: print("[DEBUG] Starting setup_gui()")
        self.setup_gui()
        if DEBUG: print("[DEBUG] Starting setup_radar()")
        self.setup_radar()

        self.data_thread = threading.Thread(target=self.collect_data, daemon=True)
        self.is_running = True
        self.data_thread.start()

        self.update_radar()
        self.root.after(500, self.ensure_focus)

    def setup_gui(self):
        self.root.configure(bg='black')
        self.setup_matplotlib_figure(self.root)
        self.status_label = ttk.Label(self.root, text="Status: Starting...", font=('TkDefaultFont', 8))
        self.status_label.pack(pady=(10, 0), fill=tk.X)
        self.setup_keyboard_bindings()

    def setup_matplotlib_figure(self, parent_frame):
        self.figure, self.ax = plt.subplots(figsize=(10.24, 6.0), dpi=100)
        self.figure.subplots_adjust(left=0.08, right=0.80, top=0.92, bottom=0.08)  # right=0.80 leaves space for legend
        self.figure.patch.set_facecolor('black')
        self.canvas = FigureCanvasTkAgg(self.figure, parent_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.get_tk_widget().bind('<Configure>', self.on_canvas_resize)

    def setup_keyboard_bindings(self):
        self.root.focus_set()
        self.root.focus_force()
        self.root.bind('<KeyPress-1>', lambda e: self.next_aircraft())
        self.root.bind('<KeyPress-2>', lambda e: self.previous_aircraft())
        self.root.bind('<KeyPress-3>', lambda e: self.stop_tracking())
        self.root.bind('<KeyPress-4>', lambda e: self.zoom_in())
        self.root.bind('<KeyPress-5>', lambda e: self.zoom_out())
        self.root.bind('<KeyPress-6>', lambda e: self.reset_view())
        self.root.bind('<KeyPress-Escape>', lambda e: self.on_closing())
        self.root.bind('<KeyPress-space>', lambda e: self.toggle_pause())
        self.root.bind('<Button-1>', self.on_click)
        self.root.configure(takefocus=True)

    def on_canvas_resize(self, event):
        try:
            self.canvas.draw_idle()
        except:
            pass

    def on_click(self, event):
        self.root.focus_set()
        self.root.focus_force()

    def ensure_focus(self):
        try:
            self.root.focus_force()
            self.root.lift()
            if hasattr(self, 'canvas'):
                self.canvas.get_tk_widget().focus_set()
        except Exception:
            pass

    def setup_radar(self):
        self.ax.set_aspect('equal')
        self.ax.set_facecolor('black')
        self.ax.grid(True, alpha=0.3, color='green')
        ring_intervals = [0.2, 0.4, 0.6, 0.8, 1.0]
        # Draw radar rings and labels first, with lower zorder
        for fraction in ring_intervals:
            ring_range = self.radar_range * fraction
            circle = Circle((0, 0), ring_range, fill=False, color='green', alpha=0.5, zorder=1)
            self.ax.add_patch(circle)
            label_x = ring_range * 0.707
            label_y = ring_range * 0.707
            self.ax.text(label_x, label_y, f'{ring_range:.0f}km',
                        fontsize=8, color='green', ha='center', va='center',
                        bbox=dict(boxstyle="round,pad=0.2", facecolor='black', alpha=0.7),
                        zorder=2)
        radar_padding = self.radar_range * 0.05
        self.ax.set_xlim(-self.radar_range - radar_padding, self.radar_range + radar_padding)
        self.ax.set_ylim(-self.radar_range - radar_padding, self.radar_range + radar_padding)
        label_fontsize = 10 if self.headless_mode else 9
        self.ax.set_xlabel('Distance East (km)', color='green', fontsize=label_fontsize)
        self.ax.set_ylabel('Distance North (km)', color='green', fontsize=label_fontsize)
        tracking_status = f" - Tracking: {self.tracked_callsign}" if self.tracked_callsign and self.tracked_callsign in self.aircraft_data else ""
        title = f'FlightGear Radar Display - Range: {self.radar_range:.0f}km{tracking_status}\nCenter: {self.center_lat:.3f}, {self.center_lon:.3f}'
        title_fontsize = 11 if self.headless_mode else 10
        self.ax.set_title(title, color='green', fontsize=title_fontsize, pad=10)
        self.ax.tick_params(colors='green', labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color('green')
            spine.set_linewidth(1.5)
        self.ax.axhline(y=0, color='green', linewidth=1.5, alpha=0.8, zorder=3)
        self.ax.axvline(x=0, color='green', linewidth=1.5, alpha=0.8, zorder=3)
        if hasattr(self, 'canvas'):
            self.canvas.draw()

    def lat_lon_to_xy(self, lat, lon):
        lat_diff = lat - self.center_lat
        lon_diff = lon - self.center_lon
        avg_lat = (lat + self.center_lat) / 2
        y = lat_diff * 111.32
        x = lon_diff * 111.32 * math.cos(math.radians(avg_lat))
        return x, y

    def next_aircraft(self):
        self.user_switched_tracking = True
        if not self.aircraft_data:
            self.update_status("No aircraft available")
            return
        aircraft_list = list(self.aircraft_data.keys())
        if not aircraft_list:
            self.update_status("No aircraft available")
            return
        if self.tracked_callsign is None:
            self.current_aircraft_index = 0
        else:
            self.current_aircraft_index = (self.current_aircraft_index + 1) % len(aircraft_list)
        self.tracked_callsign = aircraft_list[self.current_aircraft_index]
        aircraft = self.aircraft_data[self.tracked_callsign]
        self.center_lat = aircraft['lat']
        self.center_lon = aircraft['lon']
        self.radar_range = self.tracked_zoom_range
        self.update_status(f"Tracking: {self.tracked_callsign}")

    def previous_aircraft(self):
        self.user_switched_tracking = True
        if not self.aircraft_data:
            self.update_status("No aircraft available")
            return
        aircraft_list = list(self.aircraft_data.keys())
        if not aircraft_list:
            self.update_status("No aircraft available")
            return
        if self.tracked_callsign is None:
            self.current_aircraft_index = len(aircraft_list) - 1
        else:
            self.current_aircraft_index = (self.current_aircraft_index - 1) % len(aircraft_list)
        self.tracked_callsign = aircraft_list[self.current_aircraft_index]
        aircraft = self.aircraft_data[self.tracked_callsign]
        self.center_lat = aircraft['lat']
        self.center_lon = aircraft['lon']
        self.radar_range = self.tracked_zoom_range
        self.update_status(f"Tracking: {self.tracked_callsign}")

    def stop_tracking(self):
        self.user_switched_tracking = True
        self.tracked_callsign = None
        self.current_aircraft_index = 0
        self.radar_range = self.default_radar_range
        self.auto_track_attempted = False
        self.update_status("Tracking stopped")

    def zoom_in(self):
        new_range = self.radar_range * 0.8
        if new_range >= 10:
            self.radar_range = new_range
            self.update_status(f"Zoom: {self.radar_range:.0f}km")

    def zoom_out(self):
        new_range = self.radar_range * 1.25
        if new_range <= 5000:
            self.radar_range = new_range
            self.update_status(f"Zoom: {self.radar_range:.0f}km")

    def reset_view(self):
        self.user_switched_tracking = True
        self.tracked_callsign = None
        self.current_aircraft_index = 0
        self.radar_range = self.default_radar_range
        self.auto_track_attempted = False
        self.update_status("View reset")

    def toggle_pause(self):
        if not hasattr(self, 'paused'):
            self.paused = False
        self.paused = not self.paused
        status = "PAUSED" if self.paused else "RUNNING"
        self.update_status(f"Updates {status}")

    def download_elevation_data(self, lon_min, lat_min, lon_max, lat_max, output_file='srtm.tif'):
        """
        Download SRTM elevation data for the given bounding box and save as GeoTIFF.
        """
        print(f"[INFO] Downloading SRTM data for: {lon_min},{lat_min},{lon_max},{lat_max}")
        elevation.clip(bounds=(lon_min, lat_min, lon_max, lat_max), output=output_file)
        print(f"[INFO] SRTM data saved to {output_file}")

    def get_elevation(self, lat, lon, tif_file='srtm.tif'):
        """
        Get elevation (in meters) for a given lat/lon from the specified GeoTIFF file.
        """
        with rasterio.open(tif_file) as src:
            coords = [(lon, lat)]
            for val in src.sample(coords):
                elevation_val = val[0]
                if elevation_val == src.nodata:
                    return None
                return float(elevation_val)
        return None

    def download_elevation_for_tracked(self, box_km=10, output_file='srtm.tif'):
        """
        Download SRTM data centered on the tracked airplane, covering a box of box_km x box_km.
        """
        if not self.tracked_callsign or self.tracked_callsign not in self.aircraft_data:
            return
        lat = self.aircraft_data[self.tracked_callsign]['lat']
        lon = self.aircraft_data[self.tracked_callsign]['lon']
        half_box_deg = (box_km / 2) / 111.32
        min_lat = lat - half_box_deg
        max_lat = lat + half_box_deg
        min_lon = lon - half_box_deg / math.cos(math.radians(lat))
        max_lon = lon + half_box_deg / math.cos(math.radians(lat))
        print(f"[INFO] Downloading SRTM for tracked airplane at {lat:.4f},{lon:.4f}")
        self.download_elevation_data(min_lon, min_lat, max_lon, max_lat, output_file=output_file)

    def prefetch_srtm_area(self, center_lat, center_lon, box_deg=1.0, step_deg=0.01):
        """
        Prefetch SRTM elevation data in a box around center_lat, center_lon.
        box_deg: size of box in degrees (e.g., 1.0 for 1x1 degree)
        step_deg: step in degrees (smaller = more detail, 0.01 ~ 1km)
        """
        lat_min = center_lat - box_deg / 2
        lat_max = center_lat + box_deg / 2
        lon_min = center_lon - box_deg / 2
        lon_max = center_lon + box_deg / 2
        lats = np.arange(lat_min, lat_max, step_deg)
        lons = np.arange(lon_min, lon_max, step_deg)
        if DEBUG: print(f"[DEBUG] Prefetching SRTM area: lat {lat_min:.4f} to {lat_max:.4f}, lon {lon_min:.4f} to {lon_max:.4f}")
        for lat in lats:
            for lon in lons:
                elev = self.srtm_data.get_elevation(lat, lon)
                if elev is None:
                    print(f"[SRTM] Downloading tile for lat={lat:.4f}, lon={lon:.4f}")
                    #self.download_elevation_data(lon - step_deg / 2, lat - step_deg / 2, lon + step_deg / 2, lat + step_deg / 2)
                    # Uncomment the line above to download missing tiles
                    #time.sleep(0.1)  # Be nice to the server
                    # For now, just print a message
        #print(f"[SRTM] Prefetched {len(lats) * len(lons)} tiles")

    def collect_data(self):
        while self.is_running:
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((SERVER, PORT_TCP_ADMIN))
                data = b''
                sock.settimeout(2.0)
                while self.is_running:
                    try:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                    except socket.timeout:
                        break
                    except Exception as e:
                        print(f"[ERROR] Socket read error: {e}")
                        break
                if data and self.is_running:
                    response = data.decode('utf-8', errors='ignore')
                    #print("[DEBUG] RAW DATA RECEIVED:\n", response)  # Add this line
                    self.parse_aircraft_data(response)
                    self.last_update = time.time()
            except ConnectionRefusedError:
                if self.is_running:
                    print(f"[ERROR] Cannot connect to FlightGear server at {SERVER}:{PORT_TCP_ADMIN}")
                    print("[INFO] Retrying in 10 seconds...")
                    for _ in range(100):
                        if not self.is_running:
                            break
                        time.sleep(0.1)
            except Exception as e:
                if self.is_running:
                    print(f"[ERROR] Data collection error: {e}")
                    print("[INFO] Retrying in 5 seconds...")
                    for _ in range(50):
                        if not self.is_running:
                            break
                        time.sleep(0.1)
            finally:
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
            if self.is_running:
                for _ in range(10):
                    if not self.is_running:
                        break
                    time.sleep(0.1)

    def parse_aircraft_data(self, response):
        lines = response.strip().split('\n')
        new_aircraft_data = {}
        #if DEBUG: print(f"[DEBUG] Parsing aircraft data: {len(lines)} lines received")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if '@' in line and ':' in line and not line.startswith('#'):
                try:
                    parts = line.split('@', 1)
                    if len(parts) == 2:
                        callsign = parts[0].strip()
                        if callsign.startswith('# '):
                            callsign = callsign[2:]
                        rest = parts[1].split(':', 1)
                        if len(rest) == 2:
                            server_ip = rest[0].strip()
                            data_part = rest[1].strip()
                            data_parts = data_part.split()
                            if len(data_parts) >= 10:
                                x, y, z = float(data_parts[0]), float(data_parts[1]), float(data_parts[2])
                                lat, lon, alt = float(data_parts[3]), float(data_parts[4]), float(data_parts[5])
                                ox, oy, oz = float(data_parts[6]), float(data_parts[7]), float(data_parts[8])
                                model = data_parts[9] if len(data_parts) > 9 else "unknown"
                                if '/' in model:
                                    model = model.split('/')[-1]
                                if '.' in model:
                                    model = model.split('.')[0]
                                orientation_heading = math.degrees(math.atan2(ox, oy)) + 180
                                if orientation_heading >= 360:
                                    orientation_heading -= 360
                                movement_heading = orientation_heading
                                if callsign in self.aircraft_data and len(self.aircraft_history[callsign]) > 1:
                                    prev_lat, prev_lon, _ = self.aircraft_history[callsign][-1]
                                    lat_diff = lat - prev_lat
                                    lon_diff = lon - prev_lon
                                    if abs(lat_diff) > 0.00001 or abs(lon_diff) > 0.00001:
                                        movement_heading = math.degrees(math.atan2(lon_diff, lat_diff))
                                        if movement_heading < 0:
                                            movement_heading += 360
                                heading = movement_heading
                                speed = 0
                                if callsign in self.aircraft_data:
                                    prev_data = self.aircraft_data[callsign]
                                    prev_lat, prev_lon = prev_data['lat'], prev_data['lon']
                                    lat_diff = lat - prev_lat
                                    lon_diff = lon - prev_lon
                                    distance_km = math.sqrt(
                                        (lat_diff * 111.32) ** 2 +
                                        (lon_diff * 111.32 * math.cos(math.radians(lat))) ** 2
                                    )
                                    speed = (distance_km / 1.0) * 3600
                                    if speed > 1000:
                                        speed = prev_data.get('speed', 0)
                                new_aircraft_data[callsign] = {
                                    'lat': lat,
                                    'lon': lon,
                                    'alt': alt,
                                    'model': model,
                                    'heading': heading,
                                    'speed': speed,
                                    'server_ip': server_ip
                                }
                                current_time = time.time()
                                self.aircraft_history[callsign].append((lat, lon, current_time))
                                max_history_time = 60
                                self.aircraft_history[callsign] = [
                                    (lat, lon, timestamp) for lat, lon, timestamp in self.aircraft_history[callsign]
                                    if current_time - timestamp <= max_history_time
                                ][-50:]
                except (ValueError, IndexError):
                    continue
        self.aircraft_data = new_aircraft_data
        current_callsigns = set(new_aircraft_data.keys())
        offline_callsigns = set(self.aircraft_history.keys()) - current_callsigns
        for callsign in offline_callsigns:
            del self.aircraft_history[callsign]
        self.handle_auto_tracking()
        self.update_radar_center()

    def handle_auto_tracking(self):
        if not self.aircraft_data:
            return

        # Find EC-LNI and any EC-xxxx in a case-insensitive way
        ec_lni_key = None
        ec_any_key = None
        for cs in self.aircraft_data.keys():
            cs_clean = cs.strip().upper()
            if cs_clean == self.preferred_callsign.upper():
                ec_lni_key = cs
            elif cs_clean.startswith("EC") and ec_any_key is None:
                ec_any_key = cs  # Track the first EC-xxxx found if EC-LNI is not present

        # If EC-LNI is present and (never tracked before or was tracked and then disappeared), track it again
        if ec_lni_key and (not self.ec_lni_auto_tracked or self.ec_lni_lost) and not self.user_switched_tracking:
            self.tracked_callsign = ec_lni_key
            self.radar_range = self.tracked_zoom_range
            self.current_aircraft_index = list(self.aircraft_data.keys()).index(ec_lni_key)
            print(f"[TRACKING] Auto-tracking preferred aircraft: {ec_lni_key}")
            self.ec_lni_auto_tracked = True
            self.auto_track_attempted = True
            self.ec_lni_lost = False
            return

        # If EC-LNI was being tracked but now is gone, set a flag so we can auto-track it again when it reappears
        if self.ec_lni_auto_tracked and not ec_lni_key:
            self.ec_lni_lost = True

        # If tracked aircraft goes offline, reset tracking state (but allow EC-LNI to be auto-tracked again if it reappears)
        if self.tracked_callsign and self.tracked_callsign not in self.aircraft_data:
            self.tracked_callsign = None
            self.current_aircraft_index = 0
            self.radar_range = self.default_radar_range
            self.auto_track_attempted = False

        # If not tracking anything, try EC-xxxx, else any available aircraft (random selection)
        if (not self.tracked_callsign and not self.auto_track_attempted and
                self.aircraft_data and not (ec_lni_key and not self.user_switched_tracking)):
            if ec_any_key:
                self.tracked_callsign = ec_any_key
                self.current_aircraft_index = list(self.aircraft_data.keys()).index(ec_any_key)
                print(f"[TRACKING] Auto-tracking EC-xxxx aircraft: {ec_any_key}")
            else:
                available_aircraft = list(self.aircraft_data.keys())
                import random
                self.tracked_callsign = random.choice(available_aircraft)
                self.current_aircraft_index = available_aircraft.index(self.tracked_callsign)
                print(f"[TRACKING] Auto-tracking random aircraft: {self.tracked_callsign}")
            self.radar_range = self.tracked_zoom_range
            print(f"[INFO] Preferred aircraft '{self.preferred_callsign}' not available")
            self.auto_track_attempted = True
        #if DEBUG: print(f"[DEBUG] handle_auto_tracking: tracked_callsign={self.tracked_callsign}")

    def update_radar_center(self):
        if self.tracked_callsign and self.tracked_callsign in self.aircraft_data:
            tracked_data = self.aircraft_data[self.tracked_callsign]
            self.center_lat = tracked_data['lat']
            self.center_lon = tracked_data['lon']
        elif self.aircraft_data:
            lats = [ac['lat'] for ac in self.aircraft_data.values()]
            lons = [ac['lon'] for ac in self.aircraft_data.values()]
            self.center_lat = sum(lats) / len(lats)
            self.center_lon = sum(lons) / len(lons)
        #if DEBUG: print(f"[DEBUG] update_radar_center: center_lat={self.center_lat}, center_lon={self.center_lon}")

    def update_radar(self):
        if not self.is_running:
            return
        if hasattr(self, 'paused') and self.paused:
            self.root.after(1000, self.update_radar)
            return
        self.ax.clear()

        # --- Always define grid variables ---
        lat_steps = 30
        lon_steps = 30
        block_size_km = (2 * self.radar_range) / lat_steps
        min_lat = self.center_lat - (self.radar_range / 111.32)
        max_lat = self.center_lat + (self.radar_range / 111.32)
        min_lon = self.center_lon - (self.radar_range / (111.32 * math.cos(math.radians(self.center_lat))))
        max_lon = self.center_lon + (self.radar_range / (111.32 * math.cos(math.radians(self.center_lat))))

        # --- Elevation and weather color steps ---
        ft_steps = [0, 500, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 12000, 15000, 20000]
        step_colors = {
            0:  "#1565C0", 1:  "#1E88E5", 2:  "#388E3C", 3:  "#81C784", 4:  "#FFF176",
            5:  "#FFD54F", 6:  "#FFA726", 7:  "#A1887F", 8:  "#8D6E63", 9:  "#BCAAA4",
            10: "#E0E0E0", 11: "#FFFFFF", 12: "#F5F5F5", 13: "#EEEEEE"
        }
        for i in range(14, len(ft_steps)-1):
            step_colors[i] = "#EEEEEE"
        legend_ft_steps = ft_steps
        legend_step_colors = step_colors

        # --- Elevation blocks ---
        try:
            block_count = 0
            download_count = 0
            for i in range(lat_steps):
                lat = min_lat + i * (block_size_km / 111.32)
                row_elev_idx = []
                for j in range(lon_steps):
                    lon = min_lon + j * (block_size_km / (111.32 * math.cos(math.radians(self.center_lat))))
                    elevation_val = self.srtm_data.get_elevation(lat, lon)
                    if elevation_val is None:
                        elev_idx = -1
                        download_count += 1
                    else:
                        elevation_ft = elevation_val * 3.28084
                        elev_idx = -1
                        for idx in range(len(ft_steps)-1):
                            if ft_steps[idx] <= elevation_ft < ft_steps[idx+1]:
                                elev_idx = idx
                                break
                    row_elev_idx.append(elev_idx)
                j = 0
                while j < lon_steps:
                    start_j = j
                    elev_idx = row_elev_idx[j]
                    while j + 1 < lon_steps and row_elev_idx[j + 1] == elev_idx:
                        j += 1
                    if elev_idx >= 0:
                        lon_start = min_lon + start_j * (block_size_km / (111.32 * math.cos(math.radians(self.center_lat))))
                        lon_end = min_lon + (j + 1) * (block_size_km / (111.32 * math.cos(math.radians(self.center_lat))))
                        x, y = self.lat_lon_to_xy(lat, lon_start)
                        x2, y2 = self.lat_lon_to_xy(lat + (block_size_km / 111.32), lon_end)
                        width = x2 - x
                        height = y2 - y
                        color = step_colors[elev_idx]
                        self.ax.add_patch(
                            plt.Rectangle((x, y), width, height, color=color, alpha=0.5, zorder=1, linewidth=0, edgecolor=None)
                        )
                        block_count += 1
                    j += 1
            if DEBUG:
                print(f"[DEBUG] Elevation block drawing complete: {block_count} blocks, {download_count} downloads")
        except Exception as e:
            print(f"[ELEVATION] Error drawing elevation blocks: {e}")

        # --- Weather blocks ---
        if SHOW_WEATHER_BLOCKS and self.radar_range < 11:
            if DEBUG: print("[DEBUG] Drawing weather blocks")
            weather_block_count = 0
            weather_cloud_count = 0
            for i in range(lat_steps):
                lat = min_lat + i * (block_size_km / 111.32)
                for j in range(lon_steps):
                    lon = min_lon + j * (block_size_km / (111.32 * math.cos(math.radians(self.center_lat))))
                    precip, clouds = self.get_weather(lat, lon)
                    x, y = self.lat_lon_to_xy(lat, lon)
                    x2, y2 = self.lat_lon_to_xy(lat + (block_size_km / 111.32),
                                                lon + (block_size_km / (111.32 * math.cos(math.radians(self.center_lat)))))
                    width = x2 - x
                    height = y2 - y
                    color = None
                    hatch = None
                    alpha = 1.0
                    zorder = 3
                    # Granular precipitation with radar colors and hatch
                    if precip is not None and precip > 50.0:
                        color = '#d800ff'  # Magenta/Purple (extreme)
                        hatch = 'xx'
                        zorder = 5
                        weather_block_count += 1
                    elif precip is not None and precip > 20.0:
                        color = '#ff0000'  # Red (very heavy)
                        hatch = 'xx'
                        zorder = 5
                        weather_block_count += 1
                    elif precip is not None and precip > 7.0:
                        color = '#ffa500'  # Orange (heavy)
                        hatch = 'xx'
                        zorder = 4
                        weather_block_count += 1
                    elif precip is not None and precip > 3.0:
                        color = '#ffff00'  # Yellow (moderate)
                        hatch = 'xx'
                        zorder = 4
                        weather_block_count += 1
                    elif precip is not None and precip > 1.0:
                        color = '#00ff00'  # Green (light-moderate)
                        hatch = 'xx'
                        zorder = 4
                        weather_block_count += 1
                    elif precip is not None and precip > 0.1:
                        color = '#3399ff'  # Blue (light)
                        hatch = 'xx'
                        zorder = 4
                        weather_block_count += 1
                    # Granular clouds: varying gray, no hatch, increasing alpha
                    elif clouds is not None and clouds > 80:
                        color = '#444444'
                        alpha = 0.7
                        hatch = None
                        zorder = 2
                        weather_cloud_count += 1
                    elif clouds is not None and clouds > 50:
                        color = '#888888'
                        alpha = 0.5
                        hatch = None
                        zorder = 2
                        weather_cloud_count += 1
                    elif clouds is not None and clouds > 20:
                        color = '#cccccc'
                        alpha = 0.3
                        hatch = None
                        zorder = 2
                        weather_cloud_count += 1
                    if color:
                        self.ax.add_patch(
                            plt.Rectangle(
                                (x, y), width, height,
                                color=color, zorder=zorder,
                                alpha=alpha if hatch is None else 1.0,
                                linewidth=0, edgecolor=color, hatch=hatch
                            )
                        )
            if DEBUG:
                print(f"[DEBUG] Weather blocks drawn: rain={weather_block_count}, clouds={weather_cloud_count}")

        # 3. Draw aircraft, trails, and labels
        tracked_text_params = None
        #if DEBUG: print("[DEBUG] Drawing aircraft and trails")
        for callsign, data in self.aircraft_data.items():
            x, y = self.lat_lon_to_xy(data['lat'], data['lon'])
            distance = math.sqrt(x*x + y*y)
            if distance <= self.radar_range:
                is_tracked = (callsign == self.tracked_callsign)
                if is_tracked:
                    self.ax.plot(x, y, 'go', markersize=12, label=callsign, zorder=10)
                else:
                    self.ax.plot(x, y, 'ro', markersize=10, label=callsign, zorder=10)
                heading_rad = math.radians(data['heading'])
                line_scale = min(self.radar_range / 25, 15)
                dx = line_scale * math.sin(heading_rad)
                dy = line_scale * math.cos(heading_rad)
                line_color = 'green' if is_tracked else 'red'
                self.ax.plot([x, x + dx], [y, y + dy], color=line_color, linewidth=3, alpha=1.0, zorder=11)
                if callsign in self.aircraft_history and len(self.aircraft_history[callsign]) > 1:
                    trail_x = []
                    trail_y = []
                    current_lat, current_lon = data['lat'], data['lon']
                    current_time = time.time()
                    max_trail_distance_km = 18.52
                    max_trail_time = 30
                    for lat, lon, timestamp in reversed(self.aircraft_history[callsign]):
                        time_diff = current_time - timestamp
                        if time_diff > max_trail_time:
                            break
                        lat_diff = lat - current_lat
                        lon_diff = lon - current_lon
                        distance_from_current = math.sqrt(
                            (lat_diff * 111.32) ** 2 +
                            (lon_diff * 111.32 * math.cos(math.radians(lat))) ** 2
                        )
                        if distance_from_current <= max_trail_distance_km:
                            tx, ty = self.lat_lon_to_xy(lat, lon)
                            trail_x.insert(0, tx)
                            trail_y.insert(0, ty)
                    if len(trail_x) > 1:
                        self.ax.plot(trail_x, trail_y, color='yellow', alpha=0.4, linewidth=1.5,
                                   linestyle=':', markersize=0, zorder=9)
                speed_kts = data['speed'] * 0.539957 if data['speed'] > 0 else 0
                speed_text = f"{speed_kts:.0f} kts" if speed_kts > 0 else "0 kts"
                callsign_text = f"{callsign} [TRACKED]" if is_tracked else callsign
                label_color = 'lightgreen' if is_tracked else 'yellow'
                text_offset = max(0.2, self.radar_range / 200)
                text_args = (
                    x + text_offset, y + text_offset,
                    f"{callsign_text}\n{data['model']}\n{speed_text}\n{data['alt']:.0f}ft"
                )
                text_kwargs = dict(
                    fontsize=9, color=label_color, ha='left', va='bottom',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='black', alpha=0.0)
                )
                if is_tracked:
                    tracked_text_params = (text_args, text_kwargs)
                else:
                    self.ax.text(*text_args, zorder=12, **text_kwargs)
        if tracked_text_params:
            text_args, text_kwargs = tracked_text_params
            self.ax.text(*text_args, zorder=100, **text_kwargs)

        # 4. Draw the legend last (always on top)
        if legend_ft_steps and legend_step_colors:
            if DEBUG: print("[DEBUG] Drawing elevation legend")
            self.draw_elevation_legend(self.ax, legend_ft_steps, legend_step_colors)
        if DEBUG: print("[DEBUG] Drawing weather legend")
        self.draw_weather_legend(self.ax)

        if DEBUG: print("[DEBUG] Redrawing radar rings and axes")
        self.setup_radar()  # <-- This will redraw rings, axes, labels, etc.

        self.canvas.draw()
        self.root.after(1000, self.update_radar)

    def update_status(self, message):
        if hasattr(self, 'status_label'):
            self.status_label.config(text=f"Status: {message}")
        if DEBUG: print(f"[DEBUG] Status updated: {message}")

    def detect_headless_mode(self):
        desktop_vars = ['DESKTOP_SESSION', 'XDG_CURRENT_DESKTOP', 'GNOME_DESKTOP_SESSION_ID', 'KDE_FULL_SESSION']
        for var in desktop_vars:
            if os.environ.get(var):
                return False
        try:
            self.root.wm_attributes()
            return True
        except tk.TclError:
            return False

    def on_closing(self):
        self.is_running = False
        time.sleep(1)
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass

    # Add this method to your RadarGUI class
    def draw_elevation_legend(self, ax, ft_steps, step_colors):
        import matplotlib.patches as mpatches
        legend_patches = []
        for idx in range(len(ft_steps)-1):
            label = f"{ft_steps[idx]:.0f}-{ft_steps[idx+1]:.0f} ft"
            color = step_colors[idx]
            patch = mpatches.Patch(color=color, label=label)
            legend_patches.append(patch)
        leg = ax.legend(
            handles=legend_patches,
            title="Elevation (ft)",
            loc='upper left',
            bbox_to_anchor=(1.02, 1),
            fontsize=7,
            title_fontsize=8,
            frameon=True,
            facecolor='black',
            edgecolor='gray',
            ncol=1
        )
        for text in leg.get_texts():
            text.set_color('white')
            text.set_fontweight('bold')
        if leg.get_title():
            leg.get_title().set_color('white')
            leg.get_title().set_fontweight('bold')
        ax.add_artist(leg)  # Always add as artist

    def draw_weather_legend(self, ax):
        import matplotlib.patches as mpatches
        weather_patches = [
            mpatches.Patch(color='#b3e6ff', alpha=0.4, label='Light Rain (0.1–1mm)'),
            mpatches.Patch(color='#3399ff', alpha=0.4, label='Moderate Rain (1–3mm)'),
            mpatches.Patch(color='#003366', alpha=0.5, label='Heavy Rain (>3mm)'),
            mpatches.Patch(color='#cccccc', alpha=0.3, label='Clouds (20–50%)'),
            mpatches.Patch(color='#888888', alpha=0.4, label='Clouds (50–80%)'),
            mpatches.Patch(color='#666666', alpha=0.5, label='Clouds (80–100%)'),
        ]
        if DEBUG: print("[DEBUG] Drawing weather legend")
        leg = ax.legend(
            handles=weather_patches,
            title="Weather",
            loc='upper left',
            bbox_to_anchor=(1.02, 0.35),  # Lowered further down
            fontsize=7,
            title_fontsize=8,
            frameon=True,
            facecolor='black',
            edgecolor='gray',
            ncol=1
        )
        for text in leg.get_texts():
            text.set_color('white')
            text.set_fontweight('bold')
        if leg.get_title():
            leg.get_title().set_color('white')
            leg.get_title().set_fontweight('bold')
        ax.add_artist(leg)  # Always add as artist

    def get_weather(self, lat, lon):
        """
        Fetch current precipitation (mm) and cloudcover (%) for the given lat/lon using Open-Meteo API.
        Uses a cache to avoid excessive API calls.
        Returns (precip, clouds) or (None, None) if unavailable.
        """
        lat_r = round(lat, 1)
        lon_r = round(lon, 1)
        cache_key = (lat_r, lon_r)
        now = time.time()
        # Check cache
        if cache_key in self.weather_cache:
            ts, precip, clouds = self.weather_cache[cache_key]
            if now - ts < self.weather_cache_minutes * 60:
                if DEBUG: print(f"[DEBUG] Weather cache hit for {lat_r},{lon_r}: {precip} mm, {clouds}% clouds")
                return precip, clouds
        # Fetch from API
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat_r:.4f}&longitude={lon_r:.4f}&current=precipitation,cloudcover"
            )
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                precip = data.get("current", {}).get("precipitation")
                clouds = data.get("current", {}).get("cloudcover")
                self.weather_cache[cache_key] = (now, precip, clouds)
                if DEBUG: print(f"[DEBUG] Weather API fetch for {lat_r},{lon_r}: {precip} mm, {clouds}% clouds")
                return precip, clouds
        except Exception as e:
            if DEBUG: print(f"[DEBUG] Weather fetch failed for {lat},{lon}: {e}")
        return None, None

if __name__ == '__main__':
    root = tk.Tk()
    app = RadarGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()