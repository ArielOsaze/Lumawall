// SceneBoundary — stops one broken scene from blanking the whole video.
//
// Why this exists: SceneProblem referenced an easing function it had not imported.
// The throw happened during render, React unmounted the entire tree, and every
// frame from that moment on was pure black - 46 of the 52 seconds.
//
// The failure was silent: the renderer reported success, the file was the right
// duration, and only a pixel-level scan revealed it. A scene that fails should
// cost that scene, not the video, and it must leave a visible mark so it cannot be
// mistaken for a deliberate black frame.

import React from 'react';

export default class SceneBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Surface it to the renderer, which treats any scene error as a hard failure.
    // eslint-disable-next-line no-console
    console.error('[scene:' + this.props.id + '] ' + (error && error.message));
    if (window.__sceneErrors) window.__sceneErrors.push(this.props.id + ': ' + error.message);
  }

  render() {
    if (this.state.error) {
      // A loud placeholder rather than nothing: a missing scene must be obvious in
      // a still frame, so it cannot ship unnoticed.
      return (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#2a0b0e',
            color: '#ff8b90',
            fontFamily: 'Consolas, monospace',
            fontSize: 30,
            textAlign: 'center',
            padding: 80,
          }}
        >
          scene "{this.props.id}" failed to render
          <br />
          {String(this.state.error && this.state.error.message)}
        </div>
      );
    }
    return this.props.children;
  }
}
