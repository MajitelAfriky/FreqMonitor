import tkinter as tk
import threading
import time
import numpy as np
from rtlsdr import RtlSdr

# --- KONFIGURACE TVÝCH VYSÍLAČEK ---
FREKVENCE = {
    411350000: {"name": "Inner Team\n(1)", "color": "#C0392B"},
    411650000: {"name": "Program\n(2)", "color": "#F1C40F"},
    413400000: {"name": "Trafic Mgmt.\n(3)", "color": "#27AE60"},
    150425000: {"name": "HTT\n(4)", "color": "#2980B9"}
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

class RadioMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RTL-SDR Detektor Aktivity")
        
        # Maximalizace okna
        self.root.state('zoomed')
        self.root.configure(bg="black")

        self.canvas = tk.Canvas(root, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Stavové proměnné pro text
        self.current_text = "Skenuji..."
        self.current_bg = "black"
        self.outline_offset = 8 
        
        # Při jakékoliv změně velikosti okna plátno smažeme a překreslíme
        self.canvas.bind("<Configure>", self.redraw_canvas)

        self.running = True
        
        self.scan_thread = threading.Thread(target=self.scan_loop)
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def redraw_canvas(self, event=None):
        # NUKLEÁRNÍ METODA: Smažeme úplně vše, co na Canvasu je
        self.canvas.delete("all")
        self.canvas.configure(bg=self.current_bg)
        
        # Vypočítáme přesný střed aktuálního okna
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        
        # Pokud se okno ještě nevykreslilo do šířky, přeskočíme
        if cx <= 1 or cy <= 1:
            return

        font_config = ("Helvetica", 120, "bold")
        
        # Vykreslení černého obrysu (8 čistých vrstev)
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (0,-1), (-1,0), (1,0), (0,1)]:
            self.canvas.create_text(
                cx + (dx * self.outline_offset), cy + (dy * self.outline_offset), 
                text=self.current_text, font=font_config, fill="black", justify=tk.CENTER
            )
            
        # Vykreslení bílého středu přes obrysy
        self.canvas.create_text(
            cx, cy, text=self.current_text, font=font_config, fill="white", justify=tk.CENTER
        )

    def update_display(self, text, bg_color):
        # Nastavíme nový stav a vyvoláme kompletní překreslení
        self.current_text = text
        self.current_bg = bg_color
        self.redraw_canvas()

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
                        
                # Aktualizace GUI proběhne pouze při reálné změně stavu
                if active_channel != last_displayed_channel:
                    if active_channel:
                        self.root.after(0, self.update_display, active_channel, active_color)
                    else:
                        self.root.after(0, self.update_display, "Skenuji...", "black")
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