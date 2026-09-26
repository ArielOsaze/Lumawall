### How much resources does a wallpaper need?
Lively application and wallpapers are two separate things.

Lively comes with a video player and web browser - the wallpapers are basically videos and websites.

So to answer the question - it all depends on the wallpaper you choose to run.

<img width="500" src="https://github.com/rocksdanister/lively/assets/17554161/e4d5e493-7ba6-44c8-a2b7-e1a1bc1d3b18">

> Video wallpaper using dedicated gpu video hardware

Every gpu, including Intel HD graphics have dedicated hardware to decode video - so video wallpapers should be consistent in terms of resource cost if you use the same quality video (provided you are playing supported video file by your hardware, if working correctly taskmanager will show it as **Video Decode** in **GPU Engine** section.) 

Website wallpaper resource usage will depend on its design (how often website refreshing, fps, animations..) and sometimes comes with its own performance setting under customization such as render scaling options.

_Regardless of wallpaper type, lively will completetly pause the playback of the wallpaper when fullscreen apps or games run._

Additionally lively can:
* Pause wallpaper based on running application.
* Play wallpaper only on desktop. (Wallpaper Playback -> Other Application Focused -> Pause)
* Pause wallpaper when running on battery(laptop/ups)

### Understanding Task Manager readings
Looking at Taskmanager cpu & gpu usage on the Processes tab can be misleading, because it is a relative measure based on clockspeed of the hardware.

Every cpu & gpu runs at various clockspeed based on performance demand, for example if the gpu is in low performance mode/idle (usually on desktop) with less than 500mhz the gpu usage will be very high which is still normal & consumes less power.

<img width="500" src="https://github.com/rocksdanister/lively/assets/17554161/377a13d6-0576-40d2-80ab-4d0c606d8bf1">

> High usage can be due to low clockspeed, third party utility like gpu-z can be used to observe this.

### Pause algorithms
Lively implements several logic for pausing wallpaper, can be changed by:

`Settings -> Performance -> Wallpaper Playback -> Pause Algorithm`

##### Grid (Default)

<img width="500" src="https://github.com/user-attachments/assets/20f3a9d9-5bbf-4677-84c6-b349f7710845">

_Red tiles show Window coverage._

The screen is divided into a grid (tiles), and intersection calculation is used to check if windows are visually covering the display (by default 95% coverage, settings field `ProcessMonitorGridTileCoverageThreshold`.)

This algorithm is reliable and works across most situations with any number of Window arrangement and displays.

To see the detection in real time, right-click the Lively tray icon and choose Report Bug -> Grid Detection Overlay.

##### All Process
Pauses wallpapers when any running application is covering the screen, does not work in some situations like multiple window side by side.

##### Foreground Process
Pauses wallpapers when the active application is covering the screen.

##### Direct3D
Checks if a full-screen (exclusive mode) Direct3D application is running; none of the additional performance settings have any effect in this mode, not recommended.

###### Note 
The data collected during operation is stored only in-memory and never shared anywhere.