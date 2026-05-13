import tkinter as tk
import threading
import time
import numpy as np
from rtlsdr import RtlSdr

# --- KONFIGURACE TVÝCH VYSÍLAČEK ---
# Zadej frekvence v Hertzech (např. 446.00625 MHz = 446006250)
FREKVENCE = {
    446006250: "VYSÍLAČKA 1\n(Sklad)",
    446018750: "VYSÍLAČKA 2\n(Ostraha)",
    172650000: "VYSÍLAČKA 3\n(VHF Kanál)"
}

# Hranice šumu (Squelch) - TUTO HODNOTU BUDEŠ MUSET OTESTOVAT A DOLADIT
# Čím vyšší číslo, tím silnější signál je potřeba k aktivaci obrazovky.
SQUELCH_THRESHOLD = 0.05  

class RadioMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RTL-SDR Detektor Aktivity")
        self.root.geometry("1024x600") # Výchozí velikost okna
        self.root.configure(bg="black")

        # Vytvoření obřího textu
        self.label = tk.Label(root, text="Ticho...", font=("Helvetica", 100, "bold"), fg="#333333", bg="black")
        self.label.pack(expand=True)

        self.running = True
        
        # Spustíme skenování na pozadí, aby nezamrzlo GUI
        self.scan_thread = threading.Thread(target=self.scan_loop)
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def update_display(self, text, color):
        # Tato funkce bezpečně mění text na obrazovce
        self.label.config(text=text, fg=color)

    def scan_loop(self):
        # Nastavení "hluchého a rychlého" SDR
        sdr = RtlSdr()
        sdr.sample_rate = 1e6  # 1 MHz bohatě stačí
        sdr.gain = 10          # Velmi nízký zisk, nechceme slyšet šum z dálky
        
        try:
            while self.running:
                active_channel = None
                
                # Rychle proskočíme všechny frekvence
                for freq, name in FREKVENCE.items():
                    sdr.center_freq = freq
                    time.sleep(0.05) # Důležité: RTL-SDR potřebuje zlomek vteřiny na přeladění čipu
                    
                    # Přečteme malý vzorek dat (zbytečně to nepřeháníme)
                    samples = sdr.read_samples(4096)
                    
                    # Spočítáme průměrný výkon signálu
                    power = np.mean(np.abs(samples)**2)
                    
                    if power > SQUELCH_THRESHOLD:
                        active_channel = name
                        break # Jakmile najdeme aktivitu, přestaneme skenovat a jdeme to zobrazit
                        
                # Aktualizace uživatelského rozhraní
                if active_channel:
                    # Pokud někdo mluví, zobrazíme obří červený nápis
                    self.root.after(0, self.update_display, active_channel, "#FF0000")
                    time.sleep(0.3) # Chvíli podržíme zobrazení, aby to neblikalo
                else:
                    # Pokud je klid, ztlumíme nápis do šedé
                    self.root.after(0, self.update_display, "Ticho...", "#333333")
                    
        except Exception as e:
            print(f"Chyba SDR: {e}")
        finally:
            sdr.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = RadioMonitorGUI(root)
    
    # Když zavřeš okno, korektně se vypne i SDR na pozadí
    def on_closing():
        app.running = False
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()