import tkinter as tk
import threading
import time
import numpy as np
from rtlsdr import RtlSdr

# --- KONFIGURACE TVÝCH VYSÍLAČEK ---
FREKVENCE = {
    411350000: {"name": "Inner Team\n(CH 2)", "color": "#0052cc"},
    411650000: {"name": "Program\n(CH 3)", "color": "#cc7a00"},
    157800000: {"name": "Crisis\n(CH 1)", "color": "#cc0000"}
}

# 1 #C0392B
# 2 #F1C40F
# 3 #27AE60
# 4 #2980B9
# 5 #D35400
# 6 #8E44AD
# 7 #85C1E9
# 8 #F1948A

# Hranice šumu v dB (nutno doladit podle prostředí)
SQUELCH_THRESHOLD = 35  

# --- VLASTNÍ GRAFICKÁ TŘÍDA PRO TEXTY S OBRYSEM ---
class OutlinedLabel(tk.Canvas):
    def __init__(self, parent, text="", top_left_text="", font_size=50, top_left_font_size=14, bg_color="black", text_color="white", outline_color="black", outline_width=4, **kwargs):
        super().__init__(parent, bg=bg_color, highlightthickness=0, **kwargs)
        self.current_text = text
        self.current_top_left_text = top_left_text
        self.font_size = font_size
        self.top_left_font_size = top_left_font_size
        self.bg_color = bg_color
        self.text_color = text_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        
        self.bind("<Configure>", self.redraw)

    def set_text(self, text, top_left_text="", bg_color=None):
        self.current_text = text
        self.current_top_left_text = top_left_text
        if bg_color is not None:
            self.bg_color = bg_color
        self.redraw()

    def redraw(self, event=None):
        self.delete("all")
        self.configure(bg=self.bg_color)
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w <= 1 or h <= 1:
            return

        # 1. Vykreslení hlavního textu (uprostřed)
        cx = w / 2
        cy = h / 2
        font_config = ("Helvetica", self.font_size, "bold")
        
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (0,-1), (-1,0), (1,0), (0,1)]:
            self.create_text(
                cx + (dx * self.outline_width), cy + (dy * self.outline_width), 
                text=self.current_text, font=font_config, fill=self.outline_color, justify=tk.CENTER
            )
            
        self.create_text(
            cx, cy, text=self.current_text, font=font_config, fill=self.text_color, justify=tk.CENTER
        )
        
        # 2. Vykreslení textu v levém horním rohu (čas)
        if self.current_top_left_text:
            tl_font_config = ("Helvetica", self.top_left_font_size, "bold")
            tl_outline = 2 
            
            for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (0,-1), (-1,0), (1,0), (0,1)]:
                self.create_text(
                    8 + (dx * tl_outline), 5 + (dy * tl_outline), 
                    text=self.current_top_left_text, font=tl_font_config, fill=self.outline_color, anchor=tk.NW
                )
            
            self.create_text(
                8, 5, text=self.current_top_left_text, font=tl_font_config, fill=self.text_color, anchor=tk.NW
            )

# --- HLAVNÍ LOGIKA PROGRAMU ---
class RadioMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RTL-SDR Detektor Aktivity")
        self.root.state('zoomed')
        self.root.configure(bg="black")
        
        self.history = [] 

        self.right_frame = tk.Frame(root, width=350, bg="#111111")
        self.right_frame.pack_propagate(False) 
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.left_frame = tk.Frame(root, bg="black")
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.main_display = OutlinedLabel(self.left_frame, text="Skenuji...", font_size=120, outline_width=8)
        self.main_display.pack(fill=tk.BOTH, expand=True)

        self.clock_label = tk.Label(self.right_frame, text="00:00:00", font=("Helvetica", 40, "bold"), fg="white", bg="#111111")
        self.clock_label.pack(pady=(20, 10))
        
        tk.Label(self.right_frame, text="HISTORIE", font=("Helvetica", 14, "bold"), fg="#555555", bg="#111111").pack(pady=(0, 10))

        self.history_labels = []
        # Generujeme 12 obdélníků pro historii
        for _ in range(12):
            lbl = OutlinedLabel(self.right_frame, text="", font_size=20, outline_width=3, bg_color="#111111", height=55)
            lbl.pack(fill=tk.X, padx=10, pady=3)
            self.history_labels.append(lbl)

        self.running = True
        
        self.update_ui_timer()
        self.scan_thread = threading.Thread(target=self.scan_loop)
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def update_ui_timer(self):
        current_time_str = time.strftime("%H:%M:%S")
        self.clock_label.config(text=current_time_str)
        
        for i, h_lbl in enumerate(self.history_labels):
            if i < len(self.history):
                item = self.history[i]
                rel_time = self._format_relative_time(item["ts"])
                compact_name = item["name"].replace('\n', ' ')
                
                h_lbl.set_text(text=compact_name, top_left_text=rel_time, bg_color=item["color"])
            else:
                h_lbl.set_text(text="", top_left_text="", bg_color="#111111")
        
        if self.running:
            self.root.after(1000, self.update_ui_timer)

    def _format_relative_time(self, ts):
        diff = time.time() - ts
        # Nová, zjednodušená logika času
        if diff < 60:
            return f"{int(diff)} s"
        else:
            return "> 1 min"

    def set_main_activity(self, channel_name, bg_color):
        if channel_name:
            self.main_display.set_text(channel_name, bg_color=bg_color)
            
            self.history.insert(0, {"name": channel_name, "color": bg_color, "ts": time.time()})
            # Oříznutí historie na 12 záznamů
            self.history = self.history[:12]
        else:
            self.main_display.set_text("Skenuji...", bg_color="black")

    def scan_loop(self):
        sdr = RtlSdr()
        sdr.sample_rate = 1e6
        sdr.gain = 'auto' 
        
        serazene_frekvence = sorted(FREKVENCE.items())
        
        N_SAMPLES = 4096
        BIN_SIZE = sdr.sample_rate / N_SAMPLES 
        BINS_TO_CHECK = int(25000 / BIN_SIZE) 
        HALF_BINS = BINS_TO_CHECK // 2
        
        last_displayed_channel = None 
        
        try:
            last_freq = getattr(sdr, 'center_freq', 0)
            
            while self.running:
                active_channel = None
                active_color = "black"
                
                for freq, config in serazene_frekvence:
                    skok = 0 if last_freq == 0 else abs(freq - last_freq)
                    
                    try:
                        sdr.center_freq = freq
                    except Exception:
                        time.sleep(0.1)
                        continue
                    
                    if skok > 10000000:
                        time.sleep(0.3)
                    else:
                        time.sleep(0.05)
                        
                    last_freq = freq
                    
                    _ = sdr.read_samples(N_SAMPLES)
                    samples = sdr.read_samples(N_SAMPLES)
                    
                    fft_data = np.fft.fftshift(np.fft.fft(samples))
                    power_spectrum = np.abs(fft_data)**2
                    
                    center_idx = N_SAMPLES // 2
                    channel_slice = power_spectrum[center_idx - HALF_BINS : center_idx + HALF_BINS]
                    channel_slice = np.delete(channel_slice, HALF_BINS)
                    
                    avg_power_db = 10 * np.log10(np.mean(channel_slice))
                    
                    if avg_power_db > SQUELCH_THRESHOLD:
                        active_channel = config["name"]
                        active_color = config["color"]
                        break
                        
                if active_channel != last_displayed_channel:
                    self.root.after(0, self.set_main_activity, active_channel, active_color)
                    last_displayed_channel = active_channel
                
                if active_channel:
                    time.sleep(0.5)
                    
        except Exception as e:
            print(f"Kritická chyba SDR: {e}")
        finally:
            sdr.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = RadioMonitorGUI(root)
    
    def on_closing():
        app.running = False
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()