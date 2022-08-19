# AndroidAutoClicker
An auto clicker for Android, using adb and srccpy


## Known bugs
---
- Disconnecting phone while program is connected freezes video feed. I don't know how to detect device dsiconnection properly. Initial idea was to use ```adbutils.adb.wait_for``` and poll it constantly on a different thread. But I am not sure how efficient this will be. Will leave this bug in for now.