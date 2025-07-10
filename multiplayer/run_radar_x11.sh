#!/bin/bash
# FlightGear Radar Display - X11 Setup Script
# This script helps set up the X11 environment for headless systems

echo "FlightGear Radar Display - X11 Setup"
echo "====================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "WARNING: Running as root. Consider using a regular user account."
fi

# Check if X11 is available
if ! command -v X &> /dev/null; then
    echo "ERROR: X11 server not found. Please install:"
    echo "  sudo apt-get install xorg"
    exit 1
fi

# Check if DISPLAY is set
if [ -z "$DISPLAY" ]; then
    echo "DISPLAY not set. Setting to :0"
    export DISPLAY=:0
fi

echo "Current DISPLAY: $DISPLAY"

# Check if X server is running
if ! pgrep -x "X" > /dev/null; then
    echo "WARNING: X server doesn't appear to be running."
    echo "To start X server manually:"
    echo "  sudo X :0 &"
    echo "  or"
    echo "  startx"
    echo ""
    
    #read -p "Try to start X server automatically? (y/N): " -n 1 -r
    echo
    
    echo "Starting X server..."
    sudo X :0 -ac &
    X_PID=$!
    echo "X server started with PID: $X_PID"
    sleep 2
    
    # Set up cleanup on exit
    trap "echo 'Stopping X server...'; sudo kill $X_PID 2>/dev/null" EXIT
    
fi

# Test X11 connection
echo "Testing X11 connection..."
if xdpyinfo > /dev/null 2>&1; then
    echo "✓ X11 connection successful"
else
    echo "✗ X11 connection failed"
    echo "Try: xhost +local:"
    xhost +local: 2>/dev/null
fi

# Check required Python packages
echo "Checking Python packages..."
python3 -c "import tkinter, matplotlib" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Python packages available"
else
    echo "✗ Missing Python packages. Install with:"
    echo "  sudo apt-get install python3-tk python3-matplotlib"
    exit 1
fi

# Set optimal environment variables
export MPLBACKEND=TkAgg
export PYTHONUNBUFFERED=1

echo ""
echo "Starting FlightGear Radar Display..."
echo "Press Ctrl+C to stop"
echo ""

# Start the radar GUI
python3 radar_gui.py

echo "Radar Display stopped."
