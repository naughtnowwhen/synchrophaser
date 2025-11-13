# GitHub Pages Deployment Guide - Step by Step

## 🎯 Goal

Deploy your synchrophaser simulation to GitHub Pages so anyone can access it via:
`https://yourusername.github.io/synchrophaser/`

---

## ✅ What's Ready

I've created a complete web version in the `web/` directory:

```
web/
├── index.html           ✅ Beautiful UI with controls
├── pyscript.toml        ✅ PyScript configuration
├── src/
│   ├── simulation.py    ✅ Main simulation loop
│   ├── density_field.py ✅ Your atmospheric physics
│   ├── propeller.py     ✅ Your propeller physics
│   ├── synchrophaser.py ✅ Baseline PID controller
│   ├── pfd_synchrophaser.py ✅ Advanced PFD controller
│   └── parameters.py    ✅ Configuration
└── README.md            ✅ Documentation
```

---

## 🚀 Deployment Steps

### Method 1: Deploy from `main` branch (EASIEST)

**Step 1: Commit and push the web directory**

```bash
cd /Users/petermurphy/codingHome/PPI/emulation/physicalEnv

# Add and commit
git add web/
git commit -m "Add PyScript web version for GitHub Pages"
git push origin main
```

**Step 2: Enable GitHub Pages**

1. Go to your GitHub repository: `https://github.com/yourusername/PPI`
2. Click **Settings** (top menu)
3. Click **Pages** (left sidebar)
4. Under "Build and deployment":
   - **Source:** Deploy from a branch
   - **Branch:** `main`
   - **Folder:** `/web` ← Important!
5. Click **Save**

**Step 3: Wait and visit**

- Wait 1-2 minutes for deployment
- Visit: `https://yourusername.github.io/PPI/`
- Your simulation should be live! 🎉

---

### Method 2: Deploy to `gh-pages` branch (Alternative)

**If you want a dedicated branch:**

```bash
cd /Users/petermurphy/codingHome/PPI/emulation/physicalEnv/web

# Create orphan branch (no history)
git checkout --orphan gh-pages

# Add all web files
git add .
git commit -m "Deploy synchrophaser to GitHub Pages"

# Push to gh-pages branch
git push origin gh-pages

# Go back to main
git checkout main
```

Then in GitHub Settings → Pages:
- **Branch:** `gh-pages`
- **Folder:** `/ (root)`

---

## 🧪 Test Locally First

Before deploying, test it locally:

```bash
cd web

# Start local server
python3 -m http.server 8000
```

Then open: `http://localhost:8000`

**What to check:**
- ✅ Page loads
- ✅ "Loading Python runtime..." appears
- ✅ After 3-5 seconds, visualization appears
- ✅ Buttons work (OFF/BASELINE/ADVANCED)
- ✅ Propellers move
- ✅ Info panel updates

---

## 📋 Deployment Checklist

Before deploying, verify:

- [ ] All files in `web/src/` directory
- [ ] `index.html` is in `web/` root
- [ ] `pyscript.toml` is in `web/` root
- [ ] Tested locally and works
- [ ] Committed to git
- [ ] Pushed to GitHub

---

## 🎨 Customization

### Change GitHub Username in Footer

Edit `web/index.html` line ~310:

```html
<a href="https://github.com/yourusername/synchrophaser" target="_blank">
```

Replace `yourusername` with your actual GitHub username.

### Adjust Performance

If too slow, edit `web/src/simulation.py` line 83:

```python
self.grid_x = np.linspace(0, DOMAIN_WIDTH, 40)  # Reduce this number
self.grid_y = np.linspace(-DOMAIN_HEIGHT / 2, DOMAIN_HEIGHT / 2, 25)  # And this
```

Lower numbers = faster but less detail.

---

## 🐛 Troubleshooting

### GitHub Pages shows 404

**Problem:** Files not found

**Solution:**
- Make sure you selected `/web` folder (not root)
- Wait 2-3 minutes after enabling Pages
- Check all files are committed and pushed

### "Loading Python runtime..." never completes

**Problem:** PyScript not loading

**Solution:**
- Check browser console (F12 → Console)
- Look for errors
- Try different browser (Chrome recommended)
- Check internet connection (PyScript loads from CDN)

### Page loads but simulation doesn't start

**Problem:** Python files not found

**Solution:**
- Check `web/src/` has all 5 Python files
- Check `pyscript.toml` lists all files
- Check browser console for "404" errors

### Very slow performance

**Problem:** PyScript overhead

**Solution:**
- Reduce grid resolution (see Customization above)
- Lower frame rate in `simulation.py` line 231:
  ```python
  dt = 0.05  # Instead of 0.033 (slower but less CPU)
  ```

---

## 📊 Expected Performance

**Initial Load:**
- Desktop: 3-5 seconds
- Mobile: 5-10 seconds

**Runtime:**
- Desktop: 20-30 FPS
- Mobile: 10-20 FPS

**User Requirements:**
- Modern browser (Chrome, Firefox, Edge)
- JavaScript enabled
- ~50MB RAM for Python runtime

---

## 🔗 Sharing Your Demo

Once deployed, share:

**Direct link:**
```
https://yourusername.github.io/PPI/
```

**QR Code:** Generate at qr-code-generator.com

**Embed in README:**
```markdown
## Live Demo
[Try it now!](https://yourusername.github.io/PPI/)
```

---

## 🎓 What Happens When User Visits

1. **Browser downloads:**
   - `index.html` (~15 KB)
   - PyScript library (~500 KB)
   - Python runtime (~10 MB, one-time)
   - Your Python files (~20 KB)

2. **PyScript initializes:**
   - Loads Python interpreter (WebAssembly)
   - Imports numpy, opensimplex
   - Runs `simulation.py`

3. **Simulation starts:**
   - Physics runs in browser
   - Canvas updates ~30 times/second
   - All client-side, no server!

---

## ✨ What Makes This Special

- ✅ **No installation:** Users just click a link
- ✅ **No server:** Runs entirely in browser
- ✅ **Free hosting:** GitHub Pages is free forever
- ✅ **Real Python:** Actual Python code, not JavaScript
- ✅ **Shareable:** Just send the URL
- ✅ **Mobile friendly:** Works on phones/tablets

---

## 🎯 Next Steps

1. **Deploy it!** Follow Method 1 above
2. **Test it:** Visit your GitHub Pages URL
3. **Share it:** Send link to colleagues/friends
4. **Iterate:** Make improvements and push again

---

## 📝 Quick Reference

**Deployment command:**
```bash
cd /Users/petermurphy/codingHome/PPI/emulation/physicalEnv
git add web/
git commit -m "Add web version"
git push origin main
# Then enable GitHub Pages in Settings
```

**Test locally:**
```bash
cd web
python3 -m http.server 8000
# Visit http://localhost:8000
```

**Update deployment:**
```bash
# Make changes to files in web/
git add web/
git commit -m "Update web version"
git push origin main
# GitHub Pages auto-updates in 1-2 minutes
```

---

**Ready to deploy? Let's do it!** 🚀
