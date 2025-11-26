#!/usr/bin/env python3
import os
import time
import glob
import random
import threading
import requests
import feedparser
import math
import subprocess
import tkinter as tk
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageTk, ImageOps
import sys # Added for error printing

# ================= CONFIGURATION =================
HOME_DIR = os.path.expanduser("~")
IMG_DIR = os.path.join(HOME_DIR, "slides")
LOCATION_NAME = "Karur, India"
LAT = "10.9601"
LON = "78.0766"
TIMEZONE = "Asia/Kolkata"

# Layout Settings
LEFT_WIDTH = 400
ANIMATION_SPEED = 30
REFRESH_WEATHER_MINS = 15

# NEWS SETTINGS
SCROLL_SPEED = 40 # Higher = Slower scroll
FONT_NEWS = ("DejaVu Sans", 24, "bold")
MAX_NEWS_PER_FEED = 5 # Limit the number of headlines from each feed

# BRIGHTNESS CONFIG
DAY_START = 6
NIGHT_START = 19
BRIGHTNESS_DAY = "1.0"
BRIGHTNESS_NIGHT = "0.75"

# DATA SOURCES (Multi-Source News)
NEWS_FEEDS = {
    "GLOBAL": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "INDIA": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "TAMIL_NADU": "https://www.dtnext.in/rss-feeds/top-news"
}
HEADERS = {"User-Agent": "Mozilla/5.0"}

# IMAGE PROVIDERS
PROVIDERS = [
    "https://loremflickr.com/{w}/{h}/{q}",
    "https://loremflickr.com/{w}/{h}/{q}/all"
]

KEYWORDS = [
    "nature", "landscape", "mountain", "forest", "rainy city",
    "anime wallpaper", "naruto", "demon slayer", "dragon ball z", "studio ghibli",
    "marvel", "avengers", "iron man", "spiderman", "batman",
    "tokyo night", "cyberpunk city", "japan street",
    "beautiful city", "plants", "galaxy wallpaper", "beach sunset"
]

# ================= HELPERS =================

# Use Image.LANCZOS for quality resizing
try:
    RESAMPLE_MODE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_MODE = Image.ANTIALIAS

def ensure_dir():
    Path(IMG_DIR).mkdir(parents=True, exist_ok=True)

# Shared Data
current_weather = {
    "loc": LOCATION_NAME,
    "temp": "--", "hum": "--", "cond": "Loading...", "raw_cond": "clear", "feels": "--"
}
current_news = ["Loading Headlines..."]

# ================= BACKGROUND TASKS =================

def brightness_manager():
    while True:
        try:
            hour = time.localtime().tm_hour
            if DAY_START <= hour < NIGHT_START:
                target = BRIGHTNESS_DAY
            else:
                target = BRIGHTNESS_NIGHT

            output = subprocess.check_output(["xrandr"]).decode()
            display_name = None
            for line in output.splitlines():
                if " connected" in line:
                    display_name = line.split()[0]
                    break
            if display_name:
                # Set brightness using xrandr
                subprocess.call(["xrandr", "--output", display_name, "--brightness", target])
        except Exception as e:
            # print(f"Brightness Error: {e}") # Enable for debugging
            pass
        time.sleep(600)

def weather_worker():
    # Open-Meteo API URL
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,is_day&timezone=auto"
    while True:
        try:
            r = requests.get(url, timeout=10, headers=HEADERS)
            r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = r.json()
            curr = data.get("current", {})

            temp = curr.get("temperature_2m", "--")
            feels = curr.get("apparent_temperature", "--")
            hum = curr.get("relative_humidity_2m", "--")
            code = curr.get("weather_code", 0)
            is_day = curr.get("is_day", 1)

            # Weather code mapping (already comprehensive)
            cond_text = "Clear Sky"
            raw_mode = "clear"

            if code == 0:
                cond_text = "Clear Sky"
                raw_mode = "clear" if is_day else "moon"
            elif code == 1:
                cond_text = "Mainly Clear"
                raw_mode = "clear"
            elif code == 2:
                cond_text = "Partly Cloudy"
                raw_mode = "cloud"
            elif code == 3:
                cond_text = "Overcast"
                raw_mode = "cloud"
            elif code in [45, 48]:
                cond_text = "Foggy"
                raw_mode = "cloud"
            elif 51 <= code <= 67 or 80 <= code <= 82:
                cond_text = "Rain"
                raw_mode = "rain"
            elif 71 <= code <= 77 or 85 <= code <= 86:
                cond_text = "Snow"
                raw_mode = "snow"
            elif code >= 95:
                cond_text = "Thunderstorm"
                raw_mode = "storm"

            current_weather["temp"] = f"{temp}°C"
            current_weather["feels"] = f"{feels}°C"
            current_weather["hum"] = f"{hum}%"
            current_weather["cond"] = cond_text
            current_weather["raw_cond"] = raw_mode

        except Exception as e:
            # print(f"Weather Error: {e}") # Enable for debugging
            pass
        time.sleep(REFRESH_WEATHER_MINS * 60)

def news_worker():
    global current_news
    while True:
        all_headlines = []
        for source, url in NEWS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                if feed.entries:
                    # Prepend source name to each headline for context
                    headlines = [f"[{source}] {entry.title}" for entry in feed.entries[:MAX_NEWS_PER_FEED]]
                    all_headlines.extend(headlines)
            except Exception as e:
                print(f"Error fetching {source} feed: {e}", file=sys.stderr)
                pass

        if all_headlines:
            random.shuffle(all_headlines)
            current_news = all_headlines

        time.sleep(1800) # Refresh every 30 minutes

def image_downloader_smart(width, height):
    while True:
        ensure_dir()
        try:
            files = glob.glob(f"{IMG_DIR}/*.jpg")
            if len(files) < 2:
                q = random.choice(KEYWORDS)
                rand_id = random.randint(1000, 999999)
                url = random.choice(PROVIDERS).format(w=width, h=height, q=q)
                url += f"?random={rand_id}"

                r = requests.get(url, timeout=15, headers=HEADERS)
                r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                
                if r.status_code == 200:
                    fname = f"{int(time.time())}_{rand_id}.jpg"
                    fpath = os.path.join(IMG_DIR, fname)
                    
                    # Verify and save image
                    img_data = BytesIO(r.content)
                    img = Image.open(img_data)
                    img.verify() # Checks if file is a valid image
                    
                    # Must re-open after img.verify()
                    img = Image.open(BytesIO(r.content)) 
                    if img.mode != "RGB": 
                        img = img.convert("RGB")
                    img.save(fpath, quality=90)
                else:
                    time.sleep(2)
                    continue
        except Exception as e:
            # print(f"Image Downloader Error: {e}") # Enable for debugging
            pass
        time.sleep(1)

# ================= VISUAL ENGINES =================

class WeatherCanvas(tk.Canvas):
    # ... (WeatherCanvas code remains unchanged and is correct) ...
    def __init__(self, master, width=120, height=120, bg="black"):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0)
        self.width = width
        self.height = height
        self.particles = []
        self.mode = "clear"
        self.tick = 0

    def set_mode(self, mode_text):
        if mode_text != self.mode:
            self.mode = mode_text
            self.reset_animation()

    def reset_animation(self):
        self.delete("all")
        self.particles = []
        if self.mode == "clear":
            pad = 15
            self.create_oval(pad, pad, self.width-pad, self.height-pad, fill="#FFFF00", outline="#FFA500", width=3, tags="sun")
            for i in range(0, 360, 45):
                angle = math.radians(i)
                x1 = self.width/2 + math.cos(angle) * 45
                y1 = self.height/2 + math.sin(angle) * 45
                x2 = self.width/2 + math.cos(angle) * 60
                y2 = self.height/2 + math.sin(angle) * 60
                self.create_line(x1, y1, x2, y2, fill="#FFFF00", width=4, tags="rays")
        elif self.mode in ["rain", "storm"]:
            for _ in range(20):
                x = random.randint(0, self.width)
                y = random.randint(-self.height, 0)
                length = random.randint(10, 20)
                obj = self.create_line(x, y, x, y+length, fill="#00FFFF", width=2)
                self.particles.append({"id": obj, "speed": random.randint(8, 15)})
        elif self.mode == "snow":
            for _ in range(25):
                x = random.randint(0, self.width)
                y = random.randint(-self.height, 0)
                r = random.randint(2, 4)
                obj = self.create_oval(x, y, x+r, y+r, fill="white", outline="")
                self.particles.append({"id": obj, "speed": random.randint(1, 3)})
        elif self.mode == "cloud":
            self.create_oval(20, 40, 70, 80, fill="#AAAAAA", outline="")
            self.create_oval(50, 30, 100, 80, fill="#CCCCCC", outline="")
            self.create_oval(40, 50, 90, 90, fill="#BBBBBB", outline="")

    def animate(self):
        self.tick += 1
        if self.mode == "clear":
            color = "#FFFF00" if (self.tick // 10) % 2 == 0 else "#FFD700"
            self.itemconfig("sun", outline=color)
        elif self.mode in ["rain", "storm"]:
            for p in self.particles:
                self.move(p["id"], 0, p["speed"])
                coords = self.coords(p["id"])
                if coords and coords[1] > self.height:
                    new_x = random.randint(0, self.width)
                    self.coords(p["id"], new_x, -20, new_x, -20+10)
            if self.mode == "storm" and random.randint(0, 100) > 95:
                self.configure(bg="white")
                self.after(50, lambda: self.configure(bg="black"))
        elif self.mode == "snow":
            for p in self.particles:
                self.move(p["id"], random.choice([-1, 0, 1]), p["speed"])
                coords = self.coords(p["id"])
                if coords and coords[1] > self.height:
                    new_x = random.randint(0, self.width)
                    self.coords(p["id"], new_x, -10, new_x+2, -10+2)

# ================= NEWS SCROLLER =================

class NewsScroller(tk.Canvas):
    # ... (NewsScroller code remains unchanged and is correct) ...
    def __init__(self, master, width=380, height=300, bg="black"):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0)
        self.width = width
        self.height = height
        self.text_id = None
        self.news_index = 0
        self.current_y = height
        self.delay_counter = 0
        self.state = "start"

    def update_scroll(self):
        if not current_news or current_news[0] == "Loading Headlines...":
            if not self.text_id:
                self.text_id = self.create_text(self.width/2, self.height/2,
                                               text="Loading...", font=FONT_NEWS,
                                               fill="#FFD700", width=self.width-20, anchor="center")
            self.after(100, self.update_scroll)
            return

        if self.state == "start":
            self.delete("all")
            if self.news_index >= len(current_news): self.news_index = 0
            text = current_news[self.news_index]

            # Setup text below screen
            self.text_id = self.create_text(10, self.height + 20,
                                           text=f"• {text}",
                                           font=FONT_NEWS,
                                           fill="#FFD700",
                                           width=self.width-20,
                                           anchor="nw")

            self.current_y = self.height + 20
            self.state = "scroll_in"

        elif self.state == "scroll_in":
            # Scroll up to top/middle
            if self.current_y > 10:
                step = 2
                self.move(self.text_id, 0, -step)
                self.current_y -= step
            else:
                self.state = "wait"
                self.delay_counter = 0

        elif self.state == "wait":
            # Read time
            self.delay_counter += 1
            if self.delay_counter > 100:
                self.state = "scroll_out"

        elif self.state == "scroll_out":
            # Scroll off top
            self.move(self.text_id, 0, -2)
            self.current_y -= 2

            bbox = self.bbox(self.text_id)
            if bbox and bbox[3] < 0:
                self.state = "start"
                self.news_index += 1

        self.after(SCROLL_SPEED, self.update_scroll)

# ================= MAIN GUI =================

class DashboardApp:
    def __init__(self, root):
        self.root = root
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        root.geometry(f"{screen_w}x{screen_h}+0+0")
        root.attributes('-fullscreen', True)
        root.configure(bg="black", cursor="none")

        self.right_width = screen_w - LEFT_WIDTH
        self.screen_h = screen_h

        def get_font(size, weight="normal"):
            return ("DejaVu Sans", size, weight)

        MARGIN_LEFT = 25

        # --- DYNAMIC LAYOUT ---
        current_y = 30

        # 1. TIME
        self.lbl_time = tk.Label(root, text="00:00", font=get_font(65, "bold"), bg="black", fg="white", anchor="w")
        self.lbl_time.place(x=MARGIN_LEFT, y=current_y)
        current_y += 100

        # 2. DATE
        self.lbl_date = tk.Label(root, text="...", font=get_font(22), bg="black", fg="#BBBBBB", anchor="w")
        self.lbl_date.place(x=MARGIN_LEFT, y=current_y)
        current_y += 60

        # 3. DIVIDER
        tk.Frame(root, bg="#333", height=2).place(x=MARGIN_LEFT, y=current_y, width=LEFT_WIDTH-(MARGIN_LEFT*2))
        current_y += 20

        # 4. LOCATION
        self.lbl_loc = tk.Label(root, text="...", font=get_font(20, "bold"), bg="black", fg="white", anchor="w")
        self.lbl_loc.place(x=MARGIN_LEFT, y=current_y)

        # Canvas placement relative to Location
        self.weather_anim = WeatherCanvas(root, width=120, height=120, bg="black")
        self.weather_anim.place(x=LEFT_WIDTH-140, y=current_y - 10)
        current_y += 50

        # 5. TEMP
        self.lbl_temp = tk.Label(root, text="--", font=get_font(40, "bold"), bg="black", fg="#FFFFFF", anchor="w")
        self.lbl_temp.place(x=MARGIN_LEFT, y=current_y)
        current_y += 60

        # 6. DETAILS (End of Weather Section)
        self.lbl_desc = tk.Label(root, text="...", font=get_font(16), bg="black", fg="#AAAAAA", anchor="w")
        self.lbl_desc.place(x=MARGIN_LEFT, y=current_y)
        current_y += 60

        # --- NEWS SECTION ---
        news_start_y = current_y + 20
        scroller_height = screen_h - news_start_y - 60

        # News Header (Updated for multiple sources)
        tk.Frame(root, bg="#333", height=1).place(x=MARGIN_LEFT, y=news_start_y, width=LEFT_WIDTH-(MARGIN_LEFT*2))
        tk.Label(root, text="BREAKING NEWS (Global, India, TN)", font=get_font(14, "bold"), bg="black", fg="#FF4444", anchor="w").place(x=MARGIN_LEFT, y=news_start_y + 10)

        # Scroll Area
        self.news_scroller = NewsScroller(root, width=LEFT_WIDTH-40, height=scroller_height, bg="black")
        self.news_scroller.place(x=MARGIN_LEFT, y=news_start_y + 40)
        self.news_scroller.update_scroll()

        # --- RIGHT SIDE ---
        self.lbl_img = tk.Label(root, bg="#111111", text="Loading...", fg="#333")
        self.lbl_img.place(x=LEFT_WIDTH, y=0, width=self.right_width, height=self.screen_h)

        # --- STARTUP ---
        threading.Thread(target=weather_worker, daemon=True).start()
        threading.Thread(target=news_worker, daemon=True).start()
        threading.Thread(target=brightness_manager, daemon=True).start()
        threading.Thread(target=image_downloader_smart, args=(self.right_width, self.screen_h), daemon=True).start()

        root.bind("<Escape>", lambda e: root.destroy())

        self.update_time()
        self.update_weather_ui()
        self.run_animations()
        self.consume_images()

    def update_time(self):
        now = time.localtime()
        # %I:%M %p formats time as HH:MM AM/PM
        self.lbl_time.config(text=time.strftime("%I:%M %p", now)) 
        self.lbl_date.config(text=time.strftime("%A, %d %B", now))
        self.root.after(1000, self.update_time)

    def update_weather_ui(self):
        self.lbl_loc.config(text=current_weather["loc"])
        self.lbl_temp.config(text=current_weather["temp"])
        desc = f"{current_weather['cond']}\nFeels Like: {current_weather['feels']}"
        self.lbl_desc.config(text=desc)
        self.weather_anim.set_mode(current_weather["raw_cond"])
        self.root.after(2000, self.update_weather_ui)

    def run_animations(self):
        self.weather_anim.animate()
        self.root.after(ANIMATION_SPEED, self.run_animations)

    def consume_images(self):
        files = sorted(glob.glob(f"{IMG_DIR}/*.jpg"), key=os.path.getmtime)
        if files:
            next_image_path = files[0]
            try:
                pil_img = Image.open(next_image_path)
                # Resize image to fit the right pane
                pil_img = ImageOps.fit(pil_img, (self.right_width, self.screen_h), method=RESAMPLE_MODE)
                tk_img = ImageTk.PhotoImage(pil_img)
                self.lbl_img.config(image=tk_img, text="")
                self.lbl_img.image = tk_img
                os.remove(next_image_path) # Clean up file after use
            except Exception:
                try: os.remove(next_image_path)
                except: pass
        self.root.after(10000, self.consume_images) # Change image every 10 seconds

# ================= EXECUTE =================
if __name__ == "__main__":
    try:
        # These commands are often required for running GUI apps as services on Linux
        os.environ["DISPLAY"] = ":0"
        os.system("xhost + > /dev/null 2>&1")
    except:
        pass

    root = tk.Tk()
    app = DashboardApp(root)
    root.mainloop()
