import React from 'react';
import { createRoot } from 'react-dom/client';
import Timeline from './Timeline.jsx';

// The renderer reads this after the render; any entry means a scene threw and the
// output must be rejected.
window.__sceneErrors = [];

// Catch errors that never reach a React boundary (module evaluation, event
// handlers) so they cannot be mistaken for a deliberate black frame either.
window.addEventListener('error', (e) => {
  window.__sceneErrors.push('window: ' + (e.message || 'unknown'));
});
window.addEventListener('unhandledrejection', (e) => {
  window.__sceneErrors.push('promise: ' + (e.reason && e.reason.message ? e.reason.message : e.reason));
});

createRoot(document.getElementById('root')).render(<Timeline />);
