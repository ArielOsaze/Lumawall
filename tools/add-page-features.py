"""Add the new visual and playback features to the wallpaper page.

The page is a C# verbatim string inside Program.cs. Rewriting it by hand invites a
doubled quote in the wrong place, so the new script is written here and spliced in
between the markers the method already has.

Everything added is GPU work:

  * colour, filters and the tone curve go through CSS `filter`, which Chromium runs on
    the compositor. The SVG filter it references is a feComponentTransfer, which is a
    shader.
  * flip, zoom and pan go through `transform` and `object-position`, also compositor.
  * the span geometry is `width`/`height`/`left`/`top` on the element, which the
    compositor honours without a repaint of the video itself.

Nothing here copies a frame into system memory, and nothing touches the decoder, so the
RAM work from before is unaffected.
"""

import re
import sys
from pathlib import Path

PROGRAM = Path('LumaWall/Program.cs')

NEW_STYLE = """ html,body,#stage{width:100%;height:100%;margin:0;overflow:hidden;background:transparent}
 #stage{position:relative}
 .media{position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:none;opacity:1;z-index:1;
        object-fit:cover;object-position:50% 50%;transform-origin:50% 50%;backface-visibility:hidden}
 #tone{position:absolute;width:0;height:0;pointer-events:none}
"""

NEW_SCRIPT = r""" (function(){
  var stage=document.getElementById('stage'),active=null,generation=0,paused=false,muted=true;
  // The look and playback settings, replaced wholesale by apply(). Kept as one object so
  // every reader sees a consistent set rather than a half-applied mixture.
  var opts=null;
  // Span geometry: when this display is one slice of a picture that continues onto the
  // next monitor, this is the union size and this display's offset inside it.
  var span=null;
  // Playback rate is remembered separately from the element, because a new element
  // created by prepare() has to be given the rate again - it starts at 1.
  var rate=1,pingpong=false,ppDir=1,ppArmed=false;
  function report(v){try{window.chrome.webview.postMessage(v)}catch(e){}}
  function remove(el){if(!el)return;try{el.pause()}catch(e){};try{el.removeAttribute('src');el.load()}catch(e){};try{el.remove()}catch(e){}}

  // ── the tone curve ────────────────────────────────────────────────────────
  //
  // Gamma, exposure and highlight roll-off folded into one lookup table, applied by an
  // SVG feComponentTransfer. A table rather than the feComponentTransfer 'gamma' type
  // because the roll-off is not a pure power curve, and one node is cheaper than three.
  //
  // The curve is built in JS and written into the filter, so changing a slider costs a
  // table rebuild - a few hundred arithmetic operations - and no repaint of the video.
  function toneTable(){
    var exposure=opts?Number(opts.hdrExposure||0):0;
    var highlight=opts?Number(opts.hdrHighlight||0.7):0.7;
    var gamma=opts?Number(opts.gamma||1):1;
    var hdr=opts&&opts.hdrToneMap;
    var n=17,values=[];
    for(var i=0;i<n;i++){
      var x=i/(n-1);
      var y=Math.pow(x,gamma);
      if(hdr){
        y=y*Math.pow(2,exposure);
        if(y>highlight&&highlight<1){
          var over=(y-highlight)/(1-highlight);
          y=highlight+(1-highlight)*(1-Math.exp(-over));
        }
      }
      values.push(Math.max(0,Math.min(1,y)).toFixed(4));
    }
    return values.join(' ');
  }

  function needsTone(){
    if(!opts)return false;
    return !!opts.hdrToneMap||Math.abs(Number(opts.gamma||1)-1)>0.001;
  }

  function refreshTone(){
    var node=document.getElementById('toneTable');
    if(!node)return;
    var table=toneTable();
    node.setAttribute('tableValues',table);
    var g=document.getElementById('toneG');
    var b=document.getElementById('toneB');
    if(g)g.setAttribute('tableValues',table);
    if(b)b.setAttribute('tableValues',table);
  }

  // ── the CSS filter chain ──────────────────────────────────────────────────
  //
  // Order matters: the tone curve first, because it is the transfer function, then the
  // colour adjustments, because they are grades applied to the tone-mapped image. A
  // grade before a transfer function is a different picture, and the one users expect
  // is tone first.
  var FILTERS={
    grayscale:'grayscale(1)',
    sepia:'sepia(0.85)',
    cool:'hue-rotate(-12deg) saturate(1.08) brightness(1.02)',
    warm:'hue-rotate(10deg) saturate(1.12) brightness(1.03)',
    vivid:'saturate(1.45) contrast(1.08)',
    noir:'grayscale(1) contrast(1.35) brightness(0.95)',
    dream:'saturate(1.2) brightness(1.06) contrast(0.92) blur(0.4px)'
  };

  function buildFilter(){
    if(!opts)return '';
    var parts=[];
    if(needsTone())parts.push('url(#lumaTone)');
    var extra=FILTERS[opts.filter];
    if(extra)parts.push(extra);
    var brightness=Number(opts.brightness);if(isFinite(brightness)&&Math.abs(brightness-1)>0.001)parts.push('brightness('+brightness.toFixed(3)+')');
    var contrast=Number(opts.contrast);if(isFinite(contrast)&&Math.abs(contrast-1)>0.001)parts.push('contrast('+contrast.toFixed(3)+')');
    var saturation=Number(opts.saturation);if(isFinite(saturation)&&Math.abs(saturation-1)>0.001)parts.push('saturate('+saturation.toFixed(3)+')');
    var hue=Number(opts.hue);if(isFinite(hue)&&Math.abs(hue)>0.001)parts.push('hue-rotate('+hue.toFixed(2)+'deg)');
    return parts.join(' ');
  }

  function buildTransform(){
    if(!opts)return '';
    var parts=[];
    var zoom=Number(opts.zoom);if(!isFinite(zoom)||zoom<=0)zoom=1;
    if(Math.abs(zoom-1)>0.001)parts.push('scale('+zoom.toFixed(4)+')');
    if(opts.flipHorizontal)parts.push('scaleX(-1)');
    if(opts.flipVertical)parts.push('scaleY(-1)');
    return parts.join(' ');
  }

  function buildObjectPosition(){
    if(!opts)return '50% 50%';
    var x=Number(opts.offsetX),y=Number(opts.offsetY);
    if(!isFinite(x))x=0;if(!isFinite(y))y=0;
    return (50+x*50).toFixed(2)+'% '+(50+y*50).toFixed(2)+'%';
  }

  function objectFitFor(fit){
    switch(fit){
      case 'contain':return 'contain';
      case 'fill':return 'fill';
      case 'center':return 'none';
      case 'stretch':return 'fill';
      case 'cover':default:return 'cover';
    }
  }

  // ── applying the settings ─────────────────────────────────────────────────
  //
  // A span changes the element's GEOMETRY rather than its CSS: the picture is drawn at
  // the size of the whole multi-monitor union and shifted so this monitor shows its own
  // slice. That is what makes two adjacent screens read as one continuous image - each
  // window renders the same video, and each shows the part of it that belongs to it.
  function layout(el){
    if(!el)return;
    if(span&&span.totalW>0&&span.totalH>0){
      var zoom=Number(opts&&opts.zoom);if(!isFinite(zoom)||zoom<=0)zoom=1;
      var w=span.totalW*zoom,h=span.totalH*zoom;
      var left=(span.totalW-w)/2-span.x;
      var top=(span.totalH-h)/2-span.y;
      el.style.width=w+'px';
      el.style.height=h+'px';
      el.style.left=left+'px';
      el.style.top=top+'px';
      el.style.right='auto';
      el.style.bottom='auto';
      el.style.inset='auto';
      el.style.objectFit='fill';
      el.style.objectPosition='50% 50%';
      // In span mode the geometry already carries the zoom, so the transform must not
      // apply it a second time.
      el.style.transform=buildTransform().replace(/scale\([^)]*\)/,'');
      return;
    }
    el.style.width='100%';
    el.style.height='100%';
    el.style.left='0';
    el.style.top='0';
    el.style.right='auto';
    el.style.bottom='auto';
    el.style.inset='0';
    el.style.objectFit=objectFitFor(opts?opts.fit:'cover');
    el.style.objectPosition=buildObjectPosition();
    el.style.transform=buildTransform();
  }

  function applyTo(el){
    if(!el)return;
    el.style.filter=buildFilter();
    layout(el);
    if(el.tagName==='VIDEO'){
      var r=Number(opts&&opts.playbackRate);
      if(!isFinite(r)||r<=0)r=1;
      rate=r;
      try{el.playbackRate=rate}catch(e){}
      pingpong=!!(opts&&opts.pingPong);
      try{el.loop=!pingpong}catch(e){}
      ppArmed=pingpong;
    }
  }

  function applyToActive(){applyTo(active)}

  function apply(options){
    opts=options||null;
    span=opts&&opts.span?opts.span:null;
    refreshTone();
    applyToActive();
    report('options-applied'+(opts?'':' none'));
    return true;
  }

  // Ping-pong: the element loops by default, which cannot play backwards. When the mode
  // is on, loop is disabled and this reverses the direction at each end, so the picture
  // plays forward and then back rather than jumping.
  function watchDirection(video,myGeneration){
    if(!pingpong)return;
    function tick(){
      if(myGeneration!==generation||video!==active||!video.isConnected)return;
      if(video.duration&&isFinite(video.duration)){
        var t=video.currentTime;
        if(ppDir>0&&t>=video.duration-0.06){ppDir=-1;try{video.playbackRate=-rate}catch(e){}}
        else if(ppDir<0&&t<=0.06){ppDir=1;try{video.playbackRate=rate}catch(e){}}
      }
      if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(tick);else setTimeout(tick,120);
    }
    if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(tick);else setTimeout(tick,120);
  }

  function nextPaint(fn){var fired=false;function once(){if(fired)return;fired=true;try{fn()}catch(e){}}try{requestAnimationFrame(once)}catch(e){}setTimeout(once,50)}
  function firstFrame(el,isImage,ok,fail){var done=false;function ready(){if(done)return;done=true;if(isImage||paused||el.paused||!el.requestVideoFrameCallback){nextPaint(ok);return}var fired=false;var timer=setTimeout(function(){if(fired)return;fired=true;ok()},500);el.requestVideoFrameCallback(function(){if(fired)return;fired=true;clearTimeout(timer);ok()})}if(isImage){el.onload=ready;el.onerror=fail}else{el.addEventListener('loadeddata',ready,{once:true});el.addEventListener('canplay',ready,{once:true});el.addEventListener('error',fail,{once:true});if(el.readyState>=2)ready()}}
  function element(src,isImage){var el=document.createElement(isImage?'img':'video');el.className='media';el.style.opacity='0';el.src=src;if(!isImage){el.preload='auto';el.playsInline=true;el.loop=true;el.muted=muted;el.disablePictureInPicture=true}stage.appendChild(el);return el}
  function watchLoop(video,myGeneration){var last=0;function tick(){if(myGeneration!==generation||video!==active||!video.isConnected)return;var now=video.currentTime||0;if(last>0.5&&now+0.5<last)report('loop-seamless');last=now;if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(tick);else setTimeout(tick,50)}if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(tick);else setTimeout(tick,50)}
  function prepare(src,isImage,newMuted,token,fps){generation++;var myGeneration=generation;muted=newMuted;var next=element(src,isImage);applyTo(next);if(!isImage){next.muted=muted;next.play().catch(function(){})}firstFrame(next,isImage,function(){if(myGeneration!==generation){remove(next);return}var previous=active;next.style.zIndex='2';next.style.transition='opacity 120ms linear';active=next;applyTo(next);if(paused&&!isImage)active.pause();nextPaint(function(){next.style.opacity='1'});setTimeout(function(){if(myGeneration!==generation)return;next.style.transition='';if(previous)remove(previous);if(!isImage){watchLoop(next,myGeneration);watchDirection(next,myGeneration)}},150);report('media-ready:'+token)},function(){if(myGeneration!==generation)return;remove(next);report('media-error:'+token)})}
  function setPlayback(isPaused,isMuted){
    paused=isPaused;muted=isMuted;
    if(!active||active.tagName!=='VIDEO'){report('pb-noactive:'+(active?active.tagName:'null'));return}
    active.muted=muted;
    var v=active,t0=performance.now();
    if(paused){
      v.pause();
      report('pause-ack:'+Math.round(performance.now()-t0)+' rs='+v.readyState);
    }else{
      var pr=v.play();
      if(pr&&pr.catch)pr.catch(function(e){report('resume-rejected:'+e.name)});
      var done=false;
      function mark(){
        if(done)return;done=true;
        report('resume-frame:'+Math.round(performance.now()-t0)
          +' rs='+v.readyState+' paused='+v.paused+' seeking='+v.seeking
          +' ct='+v.currentTime.toFixed(2)+' net='+v.networkState);
      }
      if(v.requestVideoFrameCallback)v.requestVideoFrameCallback(mark);else setTimeout(mark,60);
    }
  }
  function setFps(fps){}
  function state(){var v=active;return JSON.stringify({generation:generation,paused:paused,muted:muted,active:active?active.tagName:null,readyState:v&&v.tagName==='VIDEO'?v.readyState:null,currentTime:v&&v.tagName==='VIDEO'?Number((v.currentTime||0).toFixed(2)):null,videoWidth:v&&v.tagName==='VIDEO'?v.videoWidth:null,error:v&&v.error?v.error.code:null,connected:v?v.isConnected:null,elements:document.querySelectorAll('video,img').length,hasOptions:!!opts,span:span?'yes':'no',rate:rate})}
  window.luma={prepare:prepare,setPlayback:setPlayback,setFps:setFps,state:state,apply:apply};
 })();"""


def main():
    text = PROGRAM.read_text(encoding='utf-8')

    # ── the style block ──────────────────────────────────────────────────────
    style_start = text.index(" return @\"<!doctype html><html><head><meta charset='utf-8'><style>\n")
    style_body_start = text.index('\n', style_start + len(' return @"')) + 1
    style_end = text.index('</style></head><body>', style_body_start)

    # ── the SVG filter and the script ────────────────────────────────────────
    script_start = text.index('<script>\n', style_end)
    script_end = text.index('\n</script></body></html>";', script_start)

    # The tone filter lives in the document so CSS can reference it by fragment id. The
    # three channels share one table: a tone curve is per-channel identical unless the
    # user is doing something this app does not offer.
    tone_svg = (
        "<svg id='tone' xmlns='http://www.w3.org/2000/svg'>"
        "<filter id='lumaTone' color-interpolation-filters='sRGB'>"
        "<feComponentTransfer>"
        "<feFuncR id='toneR' type='table' tableValues='0 0.0625 0.125 0.1875 0.25 0.3125 0.375 0.4375 0.5 0.5625 0.625 0.6875 0.75 0.8125 0.875 0.9375 1'/>"
        "<feFuncG id='toneG' type='table' tableValues='0 0.0625 0.125 0.1875 0.25 0.3125 0.375 0.4375 0.5 0.5625 0.625 0.6875 0.75 0.8125 0.875 0.9375 1'/>"
        "<feFuncB id='toneB' type='table' tableValues='0 0.0625 0.125 0.1875 0.25 0.3125 0.375 0.4375 0.5 0.5625 0.625 0.6875 0.75 0.8125 0.875 0.9375 1'/>"
        "<feFuncA id='toneA' type='table' tableValues='0 1'/>"
        "</feComponentTransfer>"
        "</filter></svg>"
    )

    new_text = (
        text[:style_body_start]
        + NEW_STYLE
        + text[style_end:script_start]
        + tone_svg
        + '\n<script>\n'
        + NEW_SCRIPT
        + '\n</script></body></html>";'
        + text[script_end + len('\n</script></body></html>";'):]
    )

    PROGRAM.write_text(new_text, encoding='utf-8')
    print('  page rewritten: %d bytes -> %d bytes' % (len(text), len(new_text)))
    print('  tone filter present: %s' % ('lumaTone' in new_text))
    print('  apply() present:     %s' % ('apply:apply' in new_text))


if __name__ == '__main__':
    main()
