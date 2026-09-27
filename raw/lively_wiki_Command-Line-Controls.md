<img src="https://raw.githubusercontent.com/rocksdanister/lively-commandline-arduino/main/resources/rotary_demo.gif" width="450" />

Lively can be controlled with commands from terminal which allows interaction through scripts or third party applications.

## Contents
* [Instruction](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#instruction)
* [Commands](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#commands)
  * [Open App](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#open-application)
  * [Quit App](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#quit-application)
  * [Playback (Pause/Play)](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#wallpaper-playback)
  * [Volume](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#wallpaper-volume)
  * [Screenshot](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#screenshot)
  * [Desktop Icon](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#desktop-icon)
  * [Screen Saver](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#screen-saver)
  * [Set Wallpaper](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#set-wallpaper)
  * [Close Wallpaper](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#close-wallpapers)
  * [Seek Wallpaper](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#seek-wallpaper)
  * [Customize Wallpaper](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#customize-wallpaper)
  * [Placement Method](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#placement-method)
* [Python](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#python)
* [AutoHotkey](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#autohotkey)
* [Rainmeter](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#rainmeter)
* [Arduino](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls#arduino)

## Instruction
Just send the commands through its main executable (Lively.exe).

<img width="500" src="https://github.com/rocksdanister/lively/assets/17554161/384717a4-b273-45b3-aa30-a2437959fd97">

(Alternatively download the [command utility](https://github.com/rocksdanister/lively/releases/download/v2.0.4.0/lively_command_utility.zip) which includes `--help` documentation and also if required set it as [PATH](https://www.howtogeek.com/118594/how-to-edit-your-system-path-for-easy-command-line-access/) for easy access.)

For example the wallpaper audio can by muted by running the following commands

without PATH variable:

`<install_location>\lively.exe app --volume 0`

with PATH variable and command utility:

`livelycu app --volume 0`

## Commands

### Open Application
Open Lively main application.

```--showApp <state>```

**state:** true/false - open/minimize Lively tray application.

### Quit Application
Close all wallpapers and exit Lively.

```--shutdown <state>```

**state:** `true/false`

### Wallpaper Playback
Control wallpaper playback state.

```--play <state>```

**state:** `true/false` - play/pause wallpapers.

### Wallpaper Volume
Set global sound level of all wallpapers.

```--volume <value>```

**value:** Absolute volume in the range 0-100 or Increment/decrement from current value when starting with +/- respectively.

###### Examples:
`--volume 100`

`--volume +10`

### Screenshot
Take wallpaper screenshot.

```screenshot --file <file-path> --monitor <screen-id>```

**screen-id:** (optional) The screen number as seen in Lively control panel, if not given primary screen is default.

**file-path:** Screenshot savefile location (.jpg)

### Desktop Icon
Control desktop icon visibility.

```--showIcons <state>```

**state:** true/false - show/hide desktop icons.

### Screen Saver
Manage Lively screensaver.

```screensaver --<command> <state>```

**state:** true/false - start/stop.

**command:**

`show`

Show screensaver(s)

`fadeIn`

Show fade-in transition when starting screensaver, to be used alongside `show` command.

`showExclusive`

Starts exclusive screensaver mode in which:
* Lively process starts.
* No wallpaper(s) are loaded.
* Saved screensaver(s) are shown.
* No further commands are processed.
* On receiving user input screensaver closes and Lively process stops.

###### Note:

This command only has effect if app is not running, otherwise behaves same as `show` command.

This command only works with installer version of the app.

### Set Wallpaper
```setwp --file <file-path> --monitor <screen-id>```

**screen-id:** (optional) The screen number as seen in Lively control panel, if not given primary screen is default.

**file-path:** 
- Folder path containing LivelyInfo.json project file/File path of the wallpaper file (.html, .mp4..)
- `random` to set random wallpaper(s) from library as wallpaper.
- `reload` to restart wallpapers.

###### Examples:
Set wallpaper project to primary screen.

```setwp --file "C:\Users\rocks\AppData\Local\Lively Wallpaper\Library\wallpapers\xyz"```

Set wallpaper to screen 1

```setwp --file "D:\samples\video.mp4" --monitor 1```

Set random wallpaper(s) to all screen(s.)

```setwp --file random```

Set random wallpaper to screen 1

```setwp --file random --monitor 1```

###### Note:
* If the wallpaper is not already installed in the library, this command will automatically import new wallpapers - provided they are media files (video, picture..) only.
* In Microsoft Store version of Lively replace package `file-path` with LocalAppData. Example: `..AppData\Local\Packages\12030rocksdanister.LivelyWallpaper_97hta09mmv6hy\LocalCache\Local\Lively Wallpaper\Library\wallpapers\xn0quq52.bq2` -> `..AppData\Local\Lively Wallpaper\Library\wallpapers\xn0quq52.bq2`

### Close Wallpaper(s)
Closes the running wallpaper on the given screen.

```closewp --monitor <screen-id>```

**screen-id:** The screen number as seen in Lively control panel, if -1 then all wallpapers are closed.

### Seek Wallpaper
Sets wallpaper playback position.

```seekwp --monitor <screen-id> --value <seek_value>```

**screen-id:** (optional) The screen number as seen in Lively control panel, if not given primary screen is default.

**seek_value:** Playback position value, several possible combinations given below.
* Absolute: Percentage(0 to 100) value, seeks to the given percent position.

  Example: ` seekwp --value 10.5`

* Relative: Percentage(-100 to 100) value starting with + or -, seeks from the current media position.

  Example: `seekwp --value +10`

###### Special cases:
For webpages only value of 0 have effect which reloads the page.

### Customize Wallpaper
Set the [Lively Properties](https://github.com/rocksdanister/lively/wiki/Web-Guide-IV-:-Interaction) of the wallpaper.

```setprop --monitor <screen-id> --property <arg>```

**screen-id:** (optional) The screen number as seen in Lively control panel, if not given primary screen is default.

**arg:** LivelyProperty.json argument, syntax `"keyValue=value"`. 

* **keyValue:** JSON key name.
* **value:** Absolute value or Increment/decrement from current value when starting with ++/-- respectively.

Make sure to enclose the **arg** inside double quotes so that spaces in text are correctly parsed.

To get the `keyValue` navigate to the wallpaper project folder and check `LivelyProperties.json` file.

###### Examples:

To change the color control:
```json
   "backgroundColor": {
    "text": "Overlay Color",
    "type": "color",
    "value": "#C0C0C0"
  }
```

`setprop --monitor 1 --property "backgroundColor=#ff0000"`

To increment current value from 25 to 30:
```json
  "saturation": {
    "max": 100,
    "min": -100,
    "tick": 200,
    "text": "Saturation",
    "type": "slider",
    "value": 25
  }
```

`setprop --property "saturation=++5"`

To change the file in folderDropdown control: 
```json
   "imgSelect": {
    "type": "folderDropdown",
    "value": "image3.jpg",
    "text": "Image",
    "filter": "*.jpg|*.png",
    "folder": "wallpapers"
  }
```

`setprop --monitor 1 --property "imgSelect=image1.jpg"`

###### Special cases:
Reset properties: `setprop --monitor 1 --property "lively_default_settings_reload=true"`

Button press: `setprop --monitor 1 --property "button_name=true"`

The default Livelyproperty of media files can be referred [here.](https://github.com/rocksdanister/lively/wiki/Web-Guide-IV-:-Interaction#video-player)

### Placement Method
Changes the wallpaper placement method after closing the running wallpapers.

```--layout <placement>```

**placement:** per, span or duplicate.

## Python
Python scripts can be used to control Lively, for example:
```python
import subprocess

def changeProperty(name, value, monitor):
    """
    Customize running wallpaper.
    """
    runCommand(['setprop', f'--monitor={monitor}', f'--property={name}={value}'])
    return;

def setWallpaper(path, monitor):
    """
    Set a wallpaper from the library.
    """
    runCommand(['setwp', f'--monitor={monitor}', f'--file={path}'])
    return;
   
def runCommand(args):
    """
    Execute lively commandline command with the list of arguments.
    Copy Livelycu.exe to the program folder or system PATH.
    """
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.run(['Livelycu'] + args, startupinfo=si)
    return;

setWallpaper('D:\\test\\test_clip.mp4', 1)
#changeProperty('hue', 30, 1)
```

## AutoHotkey
The following [AutoHotkey](https://www.autohotkey.com/) scripts execute when `Win + Z` key is pressed.

Requires adding Lively command utility to system PATH variable.

### Audio toggle
Toggle wallpaper volume between 0 and 75.

```ahk
toggle:= false
; hotkeys - winkey-z
#z::
toggle := !toggle
If toggle
{
  Run cmd.exe /c livelycu.exe app --volume 0,,hide 
}
else
{
  Run cmd.exe /c livelycu.exe app --volume 75,,hide 
}
```

### Random Wallpaper (Easy)
Sets a random wallpaper(s) to all screen(s) when pressing `Windows Key + Z`
```ahk
; hotkeys - winkey-z
#z::
command := "livelycu.exe setwp --file random"
Run cmd.exe /c %command%,,hide
```

### Random Wallpaper (Medium)
Sets a random wallpaper by creating `wallpapers.txt` file alongside ahk script.

```ahk
; Create the array, initially empty:
Array := Array()

; Write to the array:
Loop, Read, wallpapers.txt ; This loop retrieves each line from the file, one at a time.
{
    Array.Push(A_LoopReadLine) ; Append this line to the array.
}

#z::
command := "livelycu.exe setwp --file " . """"Array[random(Array.MinIndex(), Array.MaxIndex())]""""
Run cmd.exe /c %command%,,hide

random( x, y )
{
   Random, var, %x%, %y%
   return var
}
```
###### wallpapers.txt
```
C:\Users\rocks\AppData\Local\Lively Wallpaper\Library\wallpapers\aiqzbihh.0ho
C:\Users\rocks\Documents\GIFS\Car.gif
```

### Random hue (video wallpaper)
Sets a random hue value for the running wallpaper.

```ahk
#z::
command := "livelycu.exe setprop --property hue=" . random(-100,100)
Run cmd.exe /c %command%,,hide

random( x, y )
{
   Random, var, %x%, %y%
   return var
}
```

### Seek Step (video wallpaper)
Skips forward/backward wallpaper playback position by 10 percentage.

```ahk
; hotkeys - winkey-z
#z::
command := "livelycu.exe seekwp --value +10"
Run cmd.exe /c %command%,,hide 
```

### Screen saver
Set currently running wallpaper(s) as fullscreen screen saver(s.)

```ahk
#z::
Run cmd.exe /c livelycu.exe screensaver --show true,,hide 
```

## Rainmeter

The following [Rainmeter](https://www.rainmeter.net/) meters require adding Lively command utility to system PATH variable.

### Day/Night Hue (video wallpaper)
In this example color of wallpaper is changed based on time of day.

```lua
[Rainmeter]
Update=1000
AccurateText=1

[Metadata]
Name=Lively Hue
Author=rocksdanister
Information=Cycles different video hue property based on time.
Version=1.0
License=MIT

[Variables]

[MeterDummy]
Meter=String

[MeasureRunDay]
Measure=Plugin
Plugin=RunCommand
Program=livelycu.exe
Parameter=setprop --property hue=-40
State=Hide

[MeasureRunNight]
Measure=Plugin
Plugin=RunCommand
Program=livelycu.exe
Parameter=setprop --property hue=70
State=Hide

[MeasureHour]
Measure=Time
Format=%H
IfCondition=((MeasureHour >= 6) && (MeasureHour < 18))
IfTrueAction=[!CommandMeasure "MeasureRunDay" "Run"]
IfFalseAction=[!CommandMeasure "MeasureRunNight" "Run"]
```

## Arduino

### Rotary hue changer (video only)
In this example color of wallpaper is changed using rotary hardware.

Full project files can be downloaded from [here.](https://github.com/rocksdanister/lively-commandline-arduino)