import customtkinter as ctk
import threading, time, os
import ctypes, ctypes.wintypes as wintypes
from pynput import mouse

# ─── WinAPI Setup ───────────────────────────────────────────────────────────────
SendInput        = ctypes.windll.user32.SendInput
MOUSEEVENTF_MOVE = 0x0001
ULONG_PTR        = wintypes.WPARAM

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _anonymous_ = ("i",)
    _fields_ = [
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


# ─── Preset‑Loader ──────────────────────────────────────────────────────────────
def load_presets(filename="operators.txt"):
    presets = {}
    if not os.path.isfile(filename):
        print(f"[Warnung] Preset-Datei '{filename}' nicht gefunden.")
        return presets
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 3:
                print(f"[Warnung] Ungültige Zeile in Presets: {line}")
                continue
            name, xs, ys = parts
            try:
                presets[name] = (float(xs.replace(",", ".")), float(ys.replace(",", ".")))
            except ValueError:
                print(f"[Warnung] Konnte Wert nicht als Float parsen: {line}")
    return presets


# ─── Globale Zustände ───────────────────────────────────────────────────────────
running       = True
x_recoil      = 0.0
y_recoil      = 3.0
delay_ms      = 15.0

left_pressed  = False
right_pressed = False

mode_toggle   = False  # False = Hold‑Mode, True = Toggle‑Mode
aim_enabled   = False  # Nur im Toggle‑Mode genutzt

acc_x = 0.0
acc_y = 0.0

operators = load_presets()
if not operators:
    operators = {"Default": (0.0, 3.0)}


# ─── Recoil‑Loop ────────────────────────────────────────────────────────────────
def recoil_loop():
    global acc_x, acc_y
    while running:
        if mode_toggle:
            active = left_pressed and aim_enabled
        else:
            active = left_pressed and right_pressed

        if active:
            acc_x += x_recoil
            acc_y += y_recoil
            dx = int(acc_x)
            dy = int(acc_y)
            if dx or dy:
                send_mouse_move(dx, dy)
                acc_x -= dx
                acc_y -= dy
            time.sleep(delay_ms / 1000)
        else:
            time.sleep(0.01)


# ─── Maus‑Event‑Handler ─────────────────────────────────────────────────────────
def on_click(x, y, button, pressed):
    global left_pressed, right_pressed, aim_enabled
    if button == mouse.Button.left:
        left_pressed = pressed

    elif button == mouse.Button.right:
        # im Toggle‑Mode: nur beim Loslassen toggeln
        if mode_toggle and not pressed:
            aim_enabled = not aim_enabled
            print(f"[Recoil] Aim‑Mode {'ON' if aim_enabled else 'OFF'}")
        right_pressed = pressed


# ─── GUI ───────────────────────────────────────────────────────────────────────
def start_gui():
    global x_recoil, y_recoil, delay_ms, mode_toggle, aim_enabled

    ctk.set_appearance_mode("System")
    app = ctk.CTk()
    app.title("R6 Recoil Controller")
    app.geometry("360x550")

    # Felder für X, Y, Delay
    for label_text, var in [("X Recoil (Float):", "x"), ("Y Recoil (Float):", "y"), ("Delay (ms):", "d")]:
        ctk.CTkLabel(app, text=label_text).pack(pady=(10,0))
        entry = ctk.CTkEntry(app)
        if var == "x": entry.insert(0, str(x_recoil)); x_entry = entry
        if var == "y": entry.insert(0, str(y_recoil)); y_entry = entry
        if var == "d": entry.insert(0, str(delay_ms)); delay_entry = entry
        entry.pack()

    def apply_values():
        global x_recoil, y_recoil, delay_ms, acc_x, acc_y
        try:
            x_recoil = float(x_entry.get().replace(",", "."))
            y_recoil = float(y_entry.get().replace(",", "."))
            delay_ms = float(delay_entry.get().replace(",", "."))
            acc_x = acc_y = 0.0
            print(f"[Recoil] Werte: X={x_recoil}, Y={y_recoil}, Delay={delay_ms}ms")
        except ValueError:
            pass

    ctk.CTkButton(app, text="Übernehmen", command=apply_values).pack(pady=10)

    # Switch Hold vs Toggle
    switch = ctk.CTkSwitch(app, text="Toggle‑Mode aktivieren")
    switch.pack(pady=(10, 5))
    def on_switch():
        global mode_toggle, aim_enabled
        mode_toggle = switch.get()
        aim_enabled = False
        state = "TOGGLE" if mode_toggle else "HOLD"
        print(f"[Recoil] Modus: {state}")
    switch.configure(command=on_switch)

    # Scrollframe für Operator‑Buttons
    frame = ctk.CTkScrollableFrame(app, height=300)
    frame.pack(fill="both", expand=True, padx=10, pady=(0,10))

    def select_operator(name):
        global x_recoil, y_recoil, acc_x, acc_y
        xr, yr = operators[name]
        x_recoil, y_recoil = xr, yr
        acc_x = acc_y = 0.0
        x_entry.delete(0, "end"); x_entry.insert(0, str(xr))
        y_entry.delete(0, "end"); y_entry.insert(0, str(yr))
        print(f"[Recoil] {name}: X={xr}, Y={yr}")

    for name in operators:
        btn = ctk.CTkButton(frame, text=name, command=lambda n=name: select_operator(n))
        btn.pack(fill="x", pady=2)

    app.mainloop()


# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=recoil_loop, daemon=True).start()
    mouse.Listener(on_click=on_click).start()
    start_gui()
    running = False
