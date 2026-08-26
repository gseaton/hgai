# Mutation Log

## Modified
- **ui/js/app.js** (`initViz3D()`) — Added a capture-phase `mousedown` listener on the visualization's canvas container that reassigns `controls.mouseButtons.LEFT` between the library's own default rotate action and its default pan action (reusing whichever value it already assigned to `RIGHT`, since right-click already pans by default in this library), based on `event.shiftKey` at the moment each drag starts. Left-click-drag alone still orbits the camera as before; Shift+left-click-drag now pans it (translates left/right/up/down) instead.
