## WebView2
WebView2 supports H.264 out of the box and does not require convertion.

## CefSharp

CefSharp browser plugin does not support H.264 codec due to licensing, only vp8/9 supported.

### Converting mp4(x264) videos to webm(vp8/9)
1. To convert existing video files you can use third party software such as [HandBreak](https://handbrake.fr/)
2. Open handbreak & in Source selection select the video file.
3. In **Summary** under **Format** select **WebM.**
4. In **Video** select **VP8** or **VP9** as **Video Codec.**
5. Click on **Start Encode**.
6. Video will be available in **Save As** location.

<p float="left">
  <img width="500" src="https://github.com/rocksdanister/lively/assets/17554161/6cf9748d-7763-46d7-adf3-c0d516f2c2f9">
  <img width="500" src="https://github.com/rocksdanister/lively/assets/17554161/9e27e517-3a07-45a9-8b83-0f7e27d943a4">
  <img width="500" src="https://github.com/rocksdanister/lively/assets/17554161/c917761e-af0f-4bd6-a52a-7642a8897895">
</p>

## Creating a webm video webpage
1. Create a new text file, open in notepad and paste the following code:
```html
<!DOCTYPE html>
<head>
  <style>
    body{
      margin: 0;
      overflow: hidden;
    }
    video{
      width: 100%;
      height: 100%;
    }
  </style>
</head>
<body>
  <video src="video_file_name.webm"  autoplay muted loop></video>
</body>
</html>
```
2. Save & change the file extension to html.
3. Place the video file in the same folder with the correct name: video_file_name.webm
4. (Optional) Use Livelypropertie's [Folder Dropdown](https://github.com/rocksdanister/lively/wiki/Web-Guide-IV-:-Interaction#folder-dropdown) to change video clip during playback.


