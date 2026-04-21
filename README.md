# pip-pi

Wrist control panel for a Raspberry Pi Zero — 720×400 display.

## Screen 1 — Touch Proof of Concept

Four coloured quadrants fill the display:

| Quadrant    | Colour |
|-------------|--------|
| Top-left    | Red    |
| Top-right   | Blue   |
| Bottom-left | Green  |
| Bottom-right| Yellow |

**Touch behaviour**

* A **50 px diameter white circle** is drawn at the exact touch point.
* The touched quadrant **flashes** (rapid white pulses) to confirm the touch.
* After **2 seconds** the circle is automatically removed.

## Requirements

* Python 3.7+
* pygame ≥ 2.0

```bash
pip install -r requirements.txt
```

## Running

```bash
# Desktop / development
python main.py

# Raspberry Pi (full-screen)
python main.py --fullscreen
```

Press **Esc** to quit.
Tap or click the **Exit** button in the top-right corner to close the app.
