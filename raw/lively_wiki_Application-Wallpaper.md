Lively can set any application that can render its own gui window as wallpaper.

Lively can also handle games made in Unity and Godot engine.

**_It goes without saying, do not run random applications you find on the internet as wallpaper unless you are sure it is safe._**

This feature is **not available** in Windows store version of Lively.

## Problem Importing?
Lively resizes application into small window and embeds it into Lively's own window and screen captures that region for creating preview gif during importing wallpaper. This can cause issue with application that have their own code for sizing and position and try to enter fullscreen mode..

In that case you will have to manually create Lively .zip file and import it that way to skip the import wizard:
1. Create new folder, copy application files into it and create `LivelyInfo.json` file
```json
{
  "AppVersion": "1.3.0.0",
  "Title": "App1",
  "Thumbnail": null,
  "Preview": null,
  "Desc": null,
  "Author": null,
  "License": null,
  "Contact": null,
  "Type": 0,
  "FileName": "App1.exe",
  "Arguments": null,
  "IsAbsolutePath": false
}
```
2. If application supports commandline arguments then see if there is an argument for disabling fullscreen mode and add that to the "Arguments".
3. Create zip file of the folder, making sure LivelyInfo.json is in root folder.
4. Drag'n'drop the created Lively .zip file into library.

### Notes
* Wallpaper playback pause is currently disabled for application wallpapers due to bugs.
* Make sure to check [Run in background](https://docs.unity3d.com/Manual/class-PlayerSettingsStandalone.html) for Unity application.
* Make sure to set [Fullscreen Mode](https://docs.unity3d.com/Manual/class-PlayerSettingsStandalone.html) to Windowed for Unity application.
* Godot games might require selecting `Application Godot (*exe)` in file selection dialogue.
* If the application tries to enter fullscreen mode, Lively wallpaper import wizard will fail.
* Do not try to change application position or size during runtime, Lively should be managing this.
* If the application require commandline arguments, currently there is no gui way to enter this at the moment.
* Application that open multiple window is not supported.