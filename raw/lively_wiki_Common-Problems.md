#### Having a problem, how do I get help / How to retrieve log files?
First try [searching](https://github.com/rocksdanister/lively/issues) to see if someone else have the same problem to avoid creating spam.

Right-click tray-icon -> Report Bug -> Create log report file.

<img width="226" alt="image" src="https://github.com/rocksdanister/lively/assets/17554161/469bfc76-8b8e-4e6d-9f69-f07190d9e9f2">
<img width="224" alt="image" src="https://github.com/rocksdanister/lively/assets/17554161/4308daad-a578-4e2d-929e-75c4b3096a1f">

then create a [new issue](https://github.com/rocksdanister/lively/issues) for problems or a [discussion](https://github.com/rocksdanister/lively/discussions) for questions, attach the created log file .zip, and fill out the bug report template.

#### Desktop icons are hidden when keyboard input enabled?
This is done to avoid accidental selection of icons when pressing keyboard, icon visibility can be toggled in Windows setting by right-clicking empty space on desktop View -> Show desktop icons.

<img width="312" src="https://github.com/rocksdanister/lively/assets/17554161/78e8997e-b2d8-4ca5-8d26-1dd2ddb5f08e">


#### Music wallpapers don't show albumart or track information?
The music player needs to support this Windows feature (track information should show up in Windows volume control) and for others it may be disabled by default.

For example in Spotify the following setting needs to be turned on: `show desktop overlay when media keys are used`

For some players there are plugins made by the community:

https://github.com/ModernFlyouts-Community/ModernFlyouts/blob/main/docs/GSMTC-Support-And-Popular-Apps.md

If the plugin does not work it is best to try asking the player devs directly to support this Windows feature (GSMTC.)

#### WallpaperNotFoundException/File not found message when selecting wallpaper?
Unless its a `Lively .zip` file Lively only remembers the location of the wallpaper file; the original file may have been moved or deleted. Do not use temporary location such as Downloads folder to store the files.

#### WallpaperPluginNotFoundException/Antivirus warning when selecting wallpaper?
Some Anti-virus(AV) software's heuristics system may report some part of as virus due to its high sensitivity, this is a False-Positive. 
Lively is only tested with Microsoft Security/Windows Defender from our side.

If possible try submitting the file for analysis to your AV software directly:

https://www.autohotkey.com/boards/viewtopic.php?t=62266

#### Lively does not start with Windows/ Startup is getting disabled?
This usually happens when optimizers or tweaking software modify the registry.

Try saving this as "StartupTasks.reg", merging it into the registry by double-clicking and accepting the prompt, then rebooting:
```
Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System]
"EnableFullTrustStartupTasks"=dword:00000002
"EnableUwpStartupTasks"=dword:00000002
"SupportFullTrustStartupTasks"=dword:00000001
"SupportUwpStartupTasks"=dword:00000001
```

#### Display sleep/screensaver not working?
Windows by default does not sleep when any active audio streams are open, change `Multimedia settings -> When sharing media` settings of your current Windows powerplan to `Allow the computer to enter away mode` or `Allow the computer to sleep`

If that does not work, for video wallpapers you can try disabling audio by creating:
```
# mpv.conf file in folder https://github.com/rocksdanister/lively/wiki/Video-Guide#mpv
--aid=no
```

#### Lively keeps crashing on start/performance overlay visible?
Do you have any fps overlay software like Rivatuner statistics server(RTSS) from msi afterburner or equivalent on system? 

If yes then add reduce the detection in RTSS to low, if that does not work then add exceptions to the following programs:

* `<install_location>/Plugins/UI/Lively.UI.WinUI.exe`
* `<install_location>/Plugins/Cef/Lively.PlayerCefSharp.exe`
* `<install_location>/Plugins/Mpv/mpv.exe`

#### Windows protected your pc (Smart screen warning)?
Click **More info** -> **run anyway**

#### Video wallpapers not working?
If your Windows version is N/KN additional codec installation is required: https://www.codecguide.com/windows_media_codecs.htm

For best performance GPU decode (dedicated video hardware) is used to render the wallpaper, if you experience any stability issues then turn this feature off: 
https://github.com/rocksdanister/lively/wiki/Video-Guide

If the issue persists create a bug report.

#### Laptops/systems with multiple gpu?
Windows by default may use the igpu/weaker gpu instead of the main gpu.

If performance is too slow make sure to change the gpu in windows/driver control panel for the following programs:
* `<install_location>/Plugins/UI/Lively.UI.WinUI.exe`
* `<install_location>/Plugins/Cef/Lively.PlayerCefSharp.exe`
* `<install_location>/Plugins/Mpv/mpv.exe`

[Discussion](https://github.com/rocksdanister/lively/discussions/3057)

#### Desktop Window Manager(DWM) high cpu usage?
If you have multiple monitors, make sure they are all connected and using the same gpu.

#### Some/Webpage wallpapers are not working?
Install latest Visual C++ Redistributable: [vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)

#### Can I login to websites?
Starting in June 2019 Google blocks logins from CEF based browsers to Google Services, this includes Gmail, Drive, Docs etc..

#### `Lively WndProc` and `Lively WndProc (Input)` window appears on starting the application?
If you use any third party window manager application such as glazewm create an [ignore rule.](https://github.com/glzr-io/glazewm?tab=readme-ov-file#window-rules)

#### Black square on top left?
This is a compatibility issue with [WindHawk plugin](https://github.com/rocksdanister/lively/issues/2890#issuecomment-3352704643) or other Windows modifying utility.
Add exclusion to mpv.exe and lively.exe in [WindHawk settings](https://github.com/ramensoftware/windhawk/wiki/Troubleshooting#windhawk-isnt-compatible-with-a-specific-program)