import customtkinter as ctk
import threading
import time
import ctypes
import ctypes.wintypes as wintypes
from pynput import mouse

# ─── WinAPI Setup ───────────────────────────────────────────────────────────────
SendInput       = ctypes.windll.user32.SendInput
MOUSEEVENTF_MOVE = 0x0001
ULONG_PTR       = wintypes.WPARAM  # Ersatz für wintypes.ULONG_PTR

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",         wintypes.LONG),
        ("dy",         wintypes.LONG),
        ("mouseData",  wintypes.DWORD),
        ("dwFlags",    wintypes.DWORD),
        ("time",       wintypes.DWORD),
        ("dwExtraInfo",ULONG_PTR),
    ]

class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _anonymous_ = ("i",)
    _fields_   = [
        ("type", wintypes.DWORD),
        ("i",    _I),
    ]

def send_mouse_move(dx, dy):
    inp = INPUT(type=0, mi=MOUSEINPUT(
        dx=dx, dy=dy,
        mouseData=0,
        dwFlags=MOUSEEVENTF_MOVE,
        time=0,
        dwExtraInfo=0
    ))
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

# ─── Globale Zustände ───────────────────────────────────────────────────────────
running       = True
x_recoil      = 0.0   # jetzt float
y_recoil      = 3.0   # jetzt float
delay_ms      = 15
left_pressed  = False
right_pressed = False

# Akkumulatoren für Bruchteile
acc_x = 0.0
acc_y = 0.0

# Operator‑Presets
operators = {
    "Ash":      (0.0, 3.0),
    "Thermite": (0.0, 4.0),
    "Twitch":   (-0.5, 18.2),
    # …weitere hier…
}

# ─── Recoil‑Loop ────────────────────────────────────────────────────────────────
def recoil_loop():
    global acc_x, acc_y
    while running:
        if left_pressed and right_pressed:
            # Bruchteile addieren
            acc_x += x_recoil
            acc_y += y_recoil
            # Ganzzahlanteil extrahieren
            dx = int(acc_x)
            dy = int(acc_y)
            if dx or dy:
                send_mouse_move(dx, dy)
                acc_x -= dx
                acc_y -= dy
            time.sleep(delay_ms/1000)
        else:
            time.sleep(0.01)

# ─── Maus‑Event‑Handler ─────────────────────────────────────────────────────────
def on_click(x, y, button, pressed):
    global left_pressed, right_pressed
    if button == mouse.Button.left:
        left_pressed = pressed
    elif button == mouse.Button.right:
        right_pressed = pressed

# ─── GUI ───────────────────────────────────────────────────────────────────────
def start_gui():
    global x_recoil, y_recoil, delay_ms

    app = ctk.CTk()
    app.title("R6 Recoil Controller")
    app.geometry("350x500")

    # Eingabefelder für floats
    ctk.CTkLabel(app, text="X Recoil (Float):").pack(pady=(10,0))
    x_entry = ctk.CTkEntry(app); x_entry.insert(0, str(x_recoil)); x_entry.pack()

    ctk.CTkLabel(app, text="Y Recoil (Float):").pack(pady=(10,0))
    y_entry = ctk.CTkEntry(app); y_entry.insert(0, str(y_recoil)); y_entry.pack()

    ctk.CTkLabel(app, text="Delay (ms):").pack(pady=(10,0))
    delay_entry = ctk.CTkEntry(app); delay_entry.insert(0, str(delay_ms)); delay_entry.pack()

    def apply_values():
        global x_recoil, y_recoil, delay_ms, acc_x, acc_y
        try:
            x_recoil = float(x_entry.get().replace(",","."))
            y_recoil = float(y_entry.get().replace(",","."))
            delay_ms = float(delay_entry.get().replace(",","."))
            # Akkumulatoren zurücksetzen, damit’s sauber startet
            acc_x = acc_y = 0.0
        except ValueError:
            pass

    ctk.CTkButton(app, text="Übernehmen", command=apply_values).pack(pady=10)

    # Operator‑Buttons
    frame = ctk.CTkScrollableFrame(app, height=300)
    frame.pack(fill="both", expand=True, padx=10, pady=(0,10))

    def select_operator(op):
        global x_recoil, y_recoil, acc_x, acc_y
        xr, yr = operators[op]
        x_recoil, y_recoil = xr, yr
        acc_x = acc_y = 0.0
        x_entry.delete(0, "end"); x_entry.insert(0, str(xr))
        y_entry.delete(0, "end"); y_entry.insert(0, str(yr))

    for op in operators:
        ctk.CTkButton(frame, text=op, command=lambda o=op: select_operator(o)).pack(fill="x", pady=2)

    app.mainloop()

# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=recoil_loop, daemon=True).start()
    mouse.Listener(on_click=on_click).start()
    start_gui()
    running = False
