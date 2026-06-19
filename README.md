# Dashboard Application

A fullscreen dashboard application that displays real-time weather, news headlines, and image slideshows.

## Features

- **Weather Display**: Shows current weather conditions for Karur, India using Open-Meteo API
- **News Scroller**: Displays headlines from BBC, Times of India, and DT Next
- **Image Slideshow**: Automatically downloads and displays random images
- **Auto Brightness**: Adjusts screen brightness based on time of day

## Requirements

- Python 3.6+
- Linux with X11 display server
- `xrandr` for brightness control

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/techtrainer20/localserver.git
   cd localserver
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the dashboard:
```bash
python dashboard.py
```

Press `Escape` to exit fullscreen mode and close the application.


