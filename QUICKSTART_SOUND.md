# Quick Start: Sound Feature

## Try It Now!

### 1. Run the visualization
```bash
python3 main.py
```

### 2. Enable sound
Click the **"Sound OFF"** button in the bottom-right corner

### 3. Listen to the problem
The visualization starts in **OFF mode** (no synchrophaser):
- **You will hear:** WOW-WOW-WOW beating effect
- **Why:** Propellers at different RPMs create interfering sound waves
- **This is annoying!** Passengers and crew would complain

### 4. Hear the solution
Click **"BASELINE"** button:
- **You will hear:** Smooth, steady drone
- **Why:** Synchrophaser keeps RPMs within ~1 RPM
- **Much better!** This is what real synchrophasers do

### 5. Try the advanced version
Click **"ADVANCED"** button:
- **You will hear:** Even smoother tone
- **Why:** Phase-Frequency Detector uses both phase AND frequency
- **Slightly better** than baseline (4.6% improvement)

### 6. Compare them!
Switch between modes in real-time:
- **OFF** → Strong beating (problem)
- **BASELINE** → Minimal beating (proven solution)
- **ADVANCED** → Smoothest tone (modern improvement)

---

## What You're Hearing

### The Science

**Blade Passage Frequency (BPF):**
```
BPF = (RPM / 60) × 3 blades

At 2400 RPM: BPF = 120 Hz (musical note near B2)
```

**Beating Effect:**
When two propellers differ by 5 RPM:
```
Main:     2400 RPM → 120.0 Hz
Follower: 2405 RPM → 120.25 Hz
Beat:     0.25 Hz → WOW-WOW every 4 seconds
```

**Harmonics:**
Real propeller sound has harmonics at 2×, 3×, 4× the BPF, creating a "buzzing" timbre instead of a pure tone.

---

## Troubleshooting

### "Sound not available" message?

Install sounddevice:
```bash
pip3 install sounddevice
```

Then restart the visualization.

### No sound output?

Check:
- Is the button green (ON)?
- Are speakers/headphones connected?
- Is system volume turned up?

### Sound is choppy or distorted?

Try:
- Close other audio applications
- Reduce speed multiplier (use 0.5× button)

---

## Why This Matters

**Before sound:**
- You see RPM numbers differ
- You read "62% error reduction"
- Abstract, requires interpretation

**With sound:**
- You HEAR the annoying beating
- You HEAR it become smooth
- Immediate, visceral understanding

**The problem becomes real!**

This is exactly why aircraft use synchrophasers:
- Passenger comfort
- Reduced vibration
- Quieter operation

---

## Test Sound Only

Want to test the sound system independently?

```bash
python3 propeller_sound.py
```

This runs a 4-phase demonstration:
1. Both at 2400 RPM (smooth tone)
2. 5 RPM difference (subtle beating)
3. 20 RPM difference (strong beating)
4. Back to 2400 RPM (smooth again)

Each phase plays for 3-5 seconds.

---

## Learn More

- **SOUND_FEATURE.md** - Complete technical documentation
- **SOUND_INTEGRATION_COMPLETE.md** - Implementation details
- **THREE_MODE_COMPLETE.md** - Full system documentation

---

**Enjoy the demonstration!** 🎵
