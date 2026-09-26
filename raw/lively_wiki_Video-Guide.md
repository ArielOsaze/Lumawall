Lively can play any video files as system wallpaper.

**Windows N/KN/Education** systems require installation of [additional codecs](https://www.codecguide.com/windows_media_codecs.htm) for video playback.

## Video Player Setup
Currently lively supports these video players:
* [Mpv](https://github.com/rocksdanister/lively/wiki/Video-Guide#mpv)
* [libVlc](https://github.com/rocksdanister/lively/wiki/Video-Guide#libVlc)
* [Vlc](https://github.com/rocksdanister/lively/wiki/Video-Guide#vlc)
* [Windows Media Foundation (wmf)](https://github.com/rocksdanister/lively/wiki/Video-Guide#windows-media-foundation-wmf)

<img width="500" src="https://github.com/rocksdanister/lively/assets/17554161/657b1617-ff32-4d1f-84c3-33ce0e397fe2">

**Note:** Microsoft Store version of the software only supports the default Mpv player, additional plugin cannot be installed.

### Mpv
This is the **default** and **recommended** player; uses the official mpv player build.

Custom configuration file can be used, create `mpv.conf` file in: 

`<Lively install location>\plugins\mpv\portable_config\`

or application data folder:

Installer: `C:\Users\<UserName>\AppData\Local\Lively Wallpaper\Mpv\portable_config\`

Windows store: `%LocalAppData%\Packages\12030rocksdanister.LivelyWallpaper_97hta09mmv6hy\LocalCache\Local\Lively Wallpaper\Mpv\portable_config\`

and follow the [manual](https://mpv.io/manual/master/) for mpv commands.

It is also possible to implement [Lively Properties](https://github.com/rocksdanister/lively/wiki/Web-Guide-IV-:-Interaction#video-player) with mpv commands for real-time customization. 

### libVlc
Uses official Vlc player back end.

Download asset `lively_player_libvlc.zip` from latest [release.](https://github.com/rocksdanister/lively-beta/releases/download/v2.2.1.2/lively_player_libvlc.zip)

Extract the archive and copy `libvlc` folder to `<Lively install location>\plugins\`

In settings select Wallpaper -> Video player -> libVlc

**Note:** This is currently under testing, only available in BETA version of the software.

### Vlc
Uses official Vlc player build.

[Setup instructions](https://youtu.be/8vgrsoBGoHI?t=88)

**Note:** still under development, not recommended.

### Windows Media Foundation (wmf)
Download latest [release](https://github.com/rocksdanister/lively/releases/download/v2.0.7.0/lively_wmf.zip) and extract the files to `<Lively install location>\plugins\wmf` folder.

In Settings select Wallpaper -> Video player -> wmf

## Note
For best performance GPU decode (dedicated video hardware) is used to render the wallpaper, if you experience any stability issues then turn this feature off.
