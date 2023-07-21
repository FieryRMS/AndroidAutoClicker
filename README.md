# AndroidAutoClicker

An auto clicker for Android, using adb and srccpy. This project is currently in a working state. The basic functionality is there, but there are still some bugs to work out and features to add.

## Features to add

---

- [ ] Allow control when not recording
- [ ] Clear recording
- [ ] Save recording
- [ ] Load recording
- [ ] Allow editing of recording
- [ ] Make a better way to connect to the device - currently I used the adb program to first connect to the device then refresh the list in my program to get the device. Perhaps I can streamline this process in the future.

## Known bugs

---

- need to reimplement the "swipe" action, it does not work as I thought it would. Will probably need to use the "drag" action under the hood instead.

- the video stream is kinda laggy. Idk how to fix tho.
