# Flutter Web Development Guide

## Start Development Server

### Option 1: Use the Batch Script (Recommended)
```bash
cd sellflow_app
start_web_dev.bat
```

### Option 2: Manual Command
```bash
cd sellflow_app
flutter run -d chrome --web-renderer html
```

## View in Chrome with iPhone Simulation

1. **Open the app** - It will automatically open Chrome at `http://localhost:8080`

2. **Open DevTools** - Press `F12` (Windows) or `Cmd+Shift+I` (Mac)

3. **Enable Device Toolbar** - Click the phone/tablet icon 🔍 or press `Ctrl+Shift+M` (Windows) or `Cmd+Shift+M` (Mac)

4. **Select iPhone** - Choose from dropdown:
   - iPhone
   - iPhone 12 Pro
   - iPhone 14 Pro
   - iPhone SE (2nd gen)

## Hot Reload (Auto Update)

| Action | What Happens |
|--------|--------------|
| **Save file** | Flutter automatically hot reloads your changes |
| **Press 'r'** (in terminal) | Manual hot reload |
| **Press 'R'** (in terminal) | Hot restart (full restart) |
| **Press 'q'** (in terminal) | Exit server |

## Development Tips

### Check Flutter Web Support
```bash
flutter doctor
```

### Build for Production
```bash
flutter build web
```

### Clear Build Cache
```bash
flutter clean
flutter pub get
```

### Run in Debug Mode (slower, but better for debugging)
```bash
flutter run -d chrome --debug
```

---

## If Chrome Opens with White Screen

1. **Check backend is running** - Your app needs the API at `https://sellflow-backend-0nyn.onrender.com/api/v1`

2. **Check console** - Press F12 → Console tab → Look for errors

3. **Check network** - Press F12 → Network tab → Look for failed requests

---

## Recommended Workflow

1. Start backend (if testing locally):
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. Start frontend:
   ```bash
   cd sellflow_app
   flutter run -d chrome --web-renderer html
   ```

3. Edit code → Save → Auto-reload happens!

4. When done: Press `q` in terminal to stop

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Chrome doesn't open | Open `http://localhost:8080` manually |
| App shows connection error | Check backend URL in `lib/core/config/env.dart` |
| Changes don't reload | Press `r` in terminal or `R` for full restart |
