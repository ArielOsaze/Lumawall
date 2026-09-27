Lively supports webpages as wallpaper.

Everything that works in browser will work in additional to Lively API for enhancements.

### Web Player Setup
Currently lively supports these web players:
* [WebView2 (Microsoft Edge)](https://github.com/rocksdanister/lively/wiki/Web-Player#webview2-microsoft-edge)
* [Cef (Chromium Embedded Framework)](https://github.com/rocksdanister/lively/wiki/Web-Player#cef-chromium-embedded-framework)

<img width="500" src="https://github.com/rocksdanister/lively/assets/17554161/be953264-a7d7-4eac-b540-6b8c23e9a322">

#### WebView2 (Microsoft Edge)
Uses the native operating system Chromium Edge browser.

WebView2 is included with Windows and kept up-to-date via Windows updates.
 
If it is missing you can install it by visiting [here.](https://go.microsoft.com/fwlink/p/?LinkId=2124703)

#### Cef (Chromium Embedded Framework)
Chromium rendering engine using CefSharp library.

How to install CefSharp:
1. Download the `lively_player_cefsharp.zip` plugin from [release page.](https://github.com/rocksdanister/lively/releases)
2. Extract and copy the `Cef` folder into plugin folder `<install_location>/Plugins/`
3. Select `Settings -> Wallpaper -> Web Browser -> CefSharp`

**Note:** This is not supported in Microsoft Store version of Lively.

#### Some difference between Lively web player from regular browser 
* Video/audio autoplay is allowed, no need to mute audio.
* Lively API support for [System Data](https://github.com/rocksdanister/lively/wiki/Web-Guide-V-:-System-Data) and [Input.](https://github.com/rocksdanister/lively/wiki/Web-Guide-IV-:-Interaction)
* Hyperlinks open in the same instance.
* Custom link handling for Shadertoy and Youtube.
* Right click menu is disabled.
* File downloading is disabled.
* Uses memory cache, settings and cookie gets removed on exit (disk cache can be configured in lively settings.)
* Minimal - no extension support, less RAM usage.