# Synchrophaser Simulation - Web Version

Browser-based three-mode synchrophaser visualization using PyScript.

## 🚀 Live Demo

Visit: `https://yourusername.github.io/synchrophaser/`

## 🎯 What It Does

Interactive demonstration of aircraft propeller synchrophaser technology:

- **OFF Mode:** Propellers run independently → high RPM error
- **BASELINE Mode:** PID synchrophaser → 69.5% error reduction
- **ADVANCED Mode:** Phase-Frequency Detector → 73.0% error reduction

## 🛠️ Technology Stack

- **PyScript:** Python running in the browser via WebAssembly
- **Python Physics:** OpenSimplex noise, propeller dynamics, PID control
- **HTML5 Canvas:** Real-time visualization rendering
- **GitHub Pages:** Free static hosting

## 📦 Deployment to GitHub Pages

### Option 1: Automatic Deployment (Recommended)

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Add web version"
   git push origin main
   ```

2. **Enable GitHub Pages:**
   - Go to your repository on GitHub
   - Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main`
   - Folder: `/web`
   - Click Save

3. **Wait 1-2 minutes**
   - Your site will be live at: `https://yourusername.github.io/reponame/`

### Option 2: Manual gh-pages Branch

```bash
cd web

# Create gh-pages branch
git checkout --orphan gh-pages
git add .
git commit -m "Deploy to GitHub Pages"
git push origin gh-pages

# Go back to main
git checkout main
```

Then enable GitHub Pages with source: `gh-pages` branch.

## 🔧 Local Development

### Test Locally

1. **Install a local server:**
   ```bash
   # Python 3
   cd web
   python3 -m http.server 8000
   ```

2. **Open browser:**
   ```
   http://localhost:8000
   ```

### Files Structure

```
web/
├── index.html           # Main HTML page with UI
├── pyscript.toml        # PyScript configuration
├── src/
│   ├── simulation.py    # Main simulation loop
│   ├── density_field.py # Atmospheric turbulence
│   ├── propeller.py     # Propeller physics
│   ├── synchrophaser.py # Baseline PID controller
│   ├── pfd_synchrophaser.py # Advanced PFD controller
│   └── parameters.py    # Configuration
└── README.md           # This file
```

## ⚡ Performance

**Initial Load:**
- ~3-5 seconds (downloading Python runtime)
- One-time cost per browser session

**Runtime Performance:**
- ~20-30 FPS (PyScript overhead)
- Runs entirely client-side (no server!)
- All computation on user's machine

## 🎮 Controls

- **OFF / BASELINE / ADVANCED:** Switch synchrophaser modes
- **Pause / Resume:** Pause simulation
- Watch the density field and propeller markers in real-time
- Info panel shows live stats (RPM, error, rolling average)

## 🔍 How It Works

1. **Python Runtime:** PyScript loads Python interpreter in WebAssembly
2. **Physics Simulation:** Python code runs in browser, updating at ~30 Hz
3. **Canvas Rendering:** Density field drawn using HTML5 Canvas
4. **UI Updates:** JavaScript-Python interop for controls

## 📊 Technical Details

- **Density Field:** OpenSimplex noise with fractal Brownian motion
- **Propellers:** Physics-based aerodynamic model with governor control
- **Baseline Synchrophaser:** PID controller with anti-overshoot features
- **Advanced Synchrophaser:** Phase-Frequency Detector (PLL technique)
- **Rolling Average:** 15-second window for sustained performance tracking

## 🐛 Troubleshooting

### "Loading Python runtime..." never finishes

- Check browser console for errors (F12)
- Ensure all files are present in `src/` directory
- Try a different browser (Chrome, Firefox, Edge recommended)

### Slow performance

- Normal! PyScript has ~2-3x overhead vs native Python
- Close other tabs
- Try on a faster computer

### Buttons don't work

- Wait for "Loading..." message to disappear first
- Check browser console for JavaScript errors

## 🎓 Educational Use

Perfect for:
- Aerospace engineering courses
- Control systems demonstrations
- PID tuning examples
- Phase-locked loop (PLL) visualization
- Python in the browser examples

## 📝 License

Same as parent project.

## 🤝 Credits

- Physics simulation: Claude Code assisted development
- PyScript: Anaconda, Inc.
- Deployed via GitHub Pages

---

**Enjoy the simulation!** ✈️
