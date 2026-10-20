@echo off
echo Starting Flutter Web Dev Server with Hot Reload...
echo.
echo To view in Chrome with iPhone simulation:
echo 1. Open http://localhost:8080 in Chrome
echo 2. Press F12 (or Cmd+Shift+I on Mac)
echo 3. Click the Device Toolbar icon (phone/tablet)
echo 4. Select iPhone ( or iPhone 12 Pro
echo.
echo Code changes will auto-reload! Press 'r' to manually reload, 'q' to quit.
echo.
flutter run -d chrome --web-renderer html
