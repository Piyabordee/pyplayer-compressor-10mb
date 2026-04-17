"""QVideoSlider — custom seek bar with hover preview and trim markers."""
from __future__ import annotations

import time
import math
import logging
from traceback import format_exc

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets as QtW

from pyplayer.widgets import helpers as _helpers
from colour import Color


logger = logging.getLogger('widgets.py')


class QVideoSlider(QtW.QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)                               # TODO is having stuff like this here better than in the .ui file?
        self.setMouseTracking(True)

        self.last_mouseover_time = 0
        self.last_mouseover_pos = None
        self.clamp_minimum = False                              # NOTE: essentially aliases for _helpers.gui.buttonTrimXXX.isChecked()
        self.clamp_maximum = False
        self.grabbing_clamp_minimum = False
        self.grabbing_clamp_maximum = False
        self.scrubbing = False
        self.scrub_start_frame = 0

        self.hover_font_color: QtGui.QColor = None
        self.colors: list[Color] = None
        self.color_index = 0
        self.color_order = (Color('red'), Color('blue'), Color('lime'))
        self.last_color_change_time = 0


    # pass keystrokes through to parent
    def keyPressEvent(self, event: QtGui.QKeyEvent):   return _helpers.gui.keyPressEvent(event)
    def keyReleaseEvent(self, event: QtGui.QKeyEvent): return _helpers.gui.keyReleaseEvent(event)


    def setMaximum(self, maximum: int):
        ''' Sets the maximum slider value to `maximum - 1`. If 1 or less,
            the slider and its mouse events are automatically disabled. '''
        super().setMaximum(maximum - 1)
        self.setEnabled(maximum > 1)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, maximum < 2)


    def paintEvent(self, event: QtGui.QPaintEvent):
        ''' If enabled, paints a timestamp under the mouse corresponding with
            its position over the slider relative to the current media, and
            paints a rainbow effect around trim-boundaries, if present. '''
        super().paintEvent(event)                               # perform built-in paint immediately so we can paint on top

        # handle QVideoPlayer's fullscreen controls/idle cursor timeout
        try:
            now = time.time()
            vlc = _helpers.gui.vlc
            idle_time = vlc.idle_timeout_time
            if not idle_time or idle_time > now or _helpers.gui.restarted or (_helpers.gui.player.get_state() == 5 and not _helpers.gui.mime_type == 'image'):
                if vlc.underMouse() and not _helpers.gui.actionCrop.isChecked():
                    cursor = _helpers.app.overrideCursor()               # these if's may seem excessive, but it's literally...
                    if not cursor:                              # ...12x faster than actually setting the cursor
                        _helpers.app.setOverrideCursor(QtCore.Qt.ArrowCursor)
                    elif cursor.shape() != QtCore.Qt.ArrowCursor:
                        _helpers.app.changeOverrideCursor(QtCore.Qt.ArrowCursor)

                if _helpers.gui.isFullScreen():
                    current_opacity = _helpers.gui.dockControls.windowOpacity()
                    max_opacity = _helpers.settings.spinFullScreenMaxOpacity.value() / 100
                    if current_opacity < max_opacity:
                        fps = 20
                        if _helpers.gui.player.is_playing() and _helpers.settings.checkHighPrecisionProgress.isChecked():
                            fps = max(fps, _helpers.gui.frame_rate_rounded)

                        fade_time = _helpers.settings.spinFullScreenFadeDuration.value() or 0.01
                        opacity_increment = max_opacity / (fade_time * fps)
                        _helpers.gui.dockControls.setWindowOpacity(min(current_opacity + opacity_increment, max_opacity))

            else:
                if vlc.underMouse() and not _helpers.gui.actionCrop.isChecked():
                    cursor = _helpers.app.overrideCursor()
                    if not cursor:
                        _helpers.app.setOverrideCursor(QtCore.Qt.BlankCursor)
                    elif cursor.shape() != QtCore.Qt.BlankCursor:
                        _helpers.app.changeOverrideCursor(QtCore.Qt.BlankCursor)

                if _helpers.gui.isFullScreen():
                    current_opacity = _helpers.gui.dockControls.windowOpacity()
                    min_opacity = _helpers.settings.spinFullScreenMinOpacity.value() / 100
                    if current_opacity > min_opacity:
                        fps = 20
                        if _helpers.gui.player.is_playing() and _helpers.settings.checkHighPrecisionProgress.isChecked():
                            fps = max(fps, _helpers.gui.frame_rate_rounded)

                        max_opacity = _helpers.settings.spinFullScreenMaxOpacity.value() / 100
                        fade_time = _helpers.settings.spinFullScreenFadeDuration.value() or 0.01
                        opacity_increment = max_opacity / (fade_time * fps)
                        _helpers.gui.dockControls.setWindowOpacity(max(current_opacity - opacity_increment, min_opacity))
        except:
            return

        p = QtGui.QPainter()
        p.begin(self)

        # trim start/end markers -> draw trim-boundaries
        if self.clamp_minimum or self.clamp_maximum:

            # pick current color to use for animated trim-boundaries
            if not self.colors:
                next_index = self.color_index + 1
                if next_index > len(self.color_order) - 1:
                    next_index = 0
                self.colors = list(self.color_order[next_index].range_to(self.color_order[self.color_index], int(_helpers.gui.frame_rate * 4)))
                self.color_index = next_index
            if now > self.last_color_change_time + 0.05:        # update color at a MAX of 20fps
                color = QtGui.QColor(self.colors.pop().get_hex())
                self.last_color_change_time = now
            else:
                color = QtGui.QColor(self.colors[-1].get_hex())

            color.setAlpha(100)
            pen_thick = QtGui.QPen(color, 2)
            pen_thin = QtGui.QPen(QtGui.QColor(255, 255, 255), 1)
            #pen_thick.setCapStyle(Qt.RoundCap)
            p.setBrush(QtGui.QColor(0, 0, 0, 200))

            opt = QtW.QStyleOptionSlider()
            self.initStyleOption(opt)
            groove_rect = self.style().subControlRect(QtW.QStyle.CC_Slider, opt, QtW.QStyle.SC_SliderGroove, self)
            #print(groove_rect, groove_rect.left(), groove_rect.topLeft(), dir(groove_rect))

            # draw triangle markers for start/end and cover slider outside trim TODO: this is not efficient
            # New Quick Trim: show both START and END markers when Trim button is active
            if _helpers.gui.buttonTrim.isChecked():
                # Draw START marker (minimum)
                x_start = self.rangeValueToPixelPos(_helpers.gui.minimum)
                p.setPen(pen_thick)
                p.drawRoundedRect(groove_rect.left(), groove_rect.top(), x_start, groove_rect.height(), 2, 2)
                p.setPen(pen_thin)  # ↓ triangle (pointing down)
                p.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x_start, 2), QtCore.QPoint(x_start, self.height() - 2), QtCore.QPoint(x_start - 4, int(self.height() / 2))]))

                # Draw END marker (maximum)
                x_end = self.rangeValueToPixelPos(_helpers.gui.maximum)
                p.setPen(pen_thick)
                p.drawRoundedRect(x_end, groove_rect.top(), groove_rect.width() - x_end - 1, groove_rect.height(), 2, 2)
                p.setPen(pen_thin)  # ↓ triangle (pointing down)
                p.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x_end, 2), QtCore.QPoint(x_end, self.height() - 2), QtCore.QPoint(x_end + 4, int(self.height() / 2))]))
            elif self.clamp_minimum:
                x = self.rangeValueToPixelPos(_helpers.gui.minimum)
                p.setPen(pen_thick)
                p.drawRoundedRect(groove_rect.left(), groove_rect.top(), x, groove_rect.height(), 2, 2)
                p.setPen(pen_thin)  # ↓ triangle
                p.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, 2), QtCore.QPoint(x, self.height() - 2), QtCore.QPoint(x - 4, int(self.height() / 2))]))
            if self.clamp_maximum:
                x = self.rangeValueToPixelPos(_helpers.gui.maximum)
                p.setPen(pen_thick)
                p.drawRoundedRect(x, groove_rect.top(), groove_rect.width() - x - 1, groove_rect.height(), 2, 2)
                p.setPen(pen_thin)  # ↓ triangle
                p.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, 2), QtCore.QPoint(x, self.height() - 2), QtCore.QPoint(x + 4, int(self.height() / 2))]))

        #for marker in self.markers:    # an idea for a more general implementation with an arbitrary number of "markers"
        #    x = self.rangeValueToPixelPos(marker)
        #    #print(x)
        #    #p.drawImage(pos, 0, QtGui.QImage(r'C:\cs\python\videoeditor\bin\icon.ico'))
        #    p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 1))
        #    p.setBrush(QtGui.QColor(255, 255, 255))
        #    #p.drawLine(x, 0, x, self.height())
        #    p.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, 0), QtCore.QPoint(x, self.height()), QtCore.QPoint(x + 4, self.height() / 2)]))

        # hover timestamps
        if _helpers.settings.groupHover.isChecked():                     # ↓ 0.05 looks instant but avoids flickers
            fade_time = max(0.05, _helpers.settings.spinHoverFadeDuration.value())
            if now <= self.last_mouseover_time + fade_time:
                if self.underMouse():                           # ↓ get position relative to widget
                    pos = self.mapFromGlobal(QtGui.QCursor.pos())
                    self.last_mouseover_time = now              # reset fade timer if we're still hovering
                    self.last_mouseover_pos = pos               # save last mouse position within slider
                else:
                    pos = self.last_mouseover_pos               # use last position if mouse is outside the slider

                frame = self.pixelPosToRangeValue(pos)
                h, m, s, _ = get_hms(round(_helpers.gui.duration_rounded * (frame / _helpers.gui.frame_count), 2))
                text = f'{m}:{s:02}' if _helpers.gui.duration_rounded < 3600 else f'{h}:{m:02}:{s:02}'

                size = _helpers.settings.spinHoverFontSize.value()       # TODO use currentFontChanged signals + more for performance? not needed?
                font = _helpers.settings.comboHoverFont.currentFont()
                font.setPointSize(size)
                #font.setPixelSize(size)
                p.setFont(font)
                pos.setY(int(self.height() - (self.height() - size) / 2))

                # calculate fade-alpha from 0-255 based on time since we stopped hovering. default to 255 if fading is disabled
                # TODO: I sure used a lot of different methods for fading things. should these be more unified?
                alpha = int((self.last_mouseover_time + fade_time - now) * (255 / fade_time)) if fade_time != 0.05 else 255

                if _helpers.settings.checkHoverShadow.isChecked():       # draw shadow first (as black, slightly offset text)
                    p.setPen(QtGui.QColor(0, 0, 0, alpha))      # set color to black
                    p.drawText(pos.x() + 1, pos.y() + 1, text)
                self.hover_font_color.setAlpha(alpha)
                p.setPen(self.hover_font_color)                 # set color to white
                p.drawText(pos, text)                           # draw actual text over shadow

                # my idea for using tooltips for displaying the time. works, but qt's tooltips don't refresh fast enough
                #h, m, s, _ = get_hms(round(_helpers.gui.duration_rounded * (frame / _helpers.gui.frame_count), 2))
                #self.setToolTip(f'{h}:{m:02}:{s:02}' if h else f'{m}:{s:02}')
        p.end()


    def wheelEvent(self, event: QtGui.QWheelEvent):
        ''' Page-steps along the slider while scrolling. Horizontal sliders
            are increased by scrolling down or right, vertical sliders are
            increased by scrolling up or left. '''
        up = event.angleDelta().y() > 0 or event.angleDelta().x() > 0
        if self.orientation() == Qt.Vertical:
            up = not up

        if up: forward = _helpers.settings.checkScrollUpForForwards.isChecked()
        else:  forward = not _helpers.settings.checkScrollUpForForwards.isChecked()
        _helpers.gui.page_step(step=_helpers.settings.spinScrollProgress.value() / 100, forward=forward)
        event.accept()                                          # must accept event or it gets passed to the window


    def enterEvent(self, event: QtGui.QEnterEvent):
        ''' Marks the current time when mousing-over and forces a `paintEvent`
            to begin drawing hover-timestamps. Does not require
            `setMouseTracking(True)`, as `enterEvent` fires regardless. '''
        if _helpers.gui.video:
            self.last_mouseover_time = time.time()              # save last mouseover time to use as a fade timer
            self.update()                                       # force-update to draw timestamp in self.paintEvent()
        return super().enterEvent(event)


    def mousePressEvent(self, event: QtGui.QMouseEvent):
        ''' Snaps the slider handle to the mouse cursor if left-clicked.
            Does not use the normal implementation to grab the handle,
            instead allowing it to move freely until the mouse is moved,
            ensuring a snappier experience when clicking the progress bar.
            Does not emit the `sliderPressed` signal. '''

        if event.button() == Qt.LeftButton:
            pos = event.pos()
            frame = self.pixelPosToRangeValue(pos)
            self.scrub_start_frame = frame

            # https://stackoverflow.com/questions/40100733/finding-if-a-qpolygon-contains-a-qpoint-not-giving-expected-results
            if self.clamp_minimum or self.clamp_maximum:        # ^ alternate solution by finding points inside QPolygons
                radius = 12                                     # 12 pixel radius for the handles
                self.grabbing_clamp_minimum = False
                self.grabbing_clamp_maximum = False
                if self.clamp_minimum:
                    min_pos = self.rangeValueToPixelPos(_helpers.gui.minimum)
                    if min_pos - radius < pos.x() < min_pos + radius:
                        self.grabbing_clamp_minimum = True
                        return  # Don't seek if grabbing START marker
                if self.clamp_maximum:
                    max_pos = self.rangeValueToPixelPos(_helpers.gui.maximum)
                    if max_pos - radius < pos.x() < max_pos + radius:
                        self.grabbing_clamp_maximum = True
                        return  # Don't seek if grabbing END marker

            # Normal seek behavior (not grabbing trim markers)
            if _helpers.gui.minimum < frame < _helpers.gui.maximum:
                _helpers.gui.player.set_and_update_progress(frame, SetProgressContext.NAVIGATION_EXACT)
            elif _helpers.gui.buttonTrim.isChecked() and frame >= _helpers.gui.minimum and frame <= _helpers.gui.sliderProgress.maximum():
                # In trim mode, also allow clicking between START and video end
                _helpers.gui.player.set_and_update_progress(frame, SetProgressContext.NAVIGATION_EXACT)
            #if abs(delta) > 0.025:                             # only change if difference between new/old positions is greater than 2.5%
            #    self.setValue(new_value)


    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        ''' If not dragging, this manually repaints the timestamp-hover effect
            while mousing over the progress bar. Otherwise, this re-implements
            scrubbing by grabbing the handle, pausing the player, and updating
            the player position. Does not emit the `sliderMoved` signal. '''

        # event.button() is always 0 for move events. yes, it's very stupid.
        if event.buttons() != Qt.LeftButton:                    # NOTE: requires `self.setMouseTracking(True)`
            self.update()

        # handle dragging
        else:
            frame = self.pixelPosToRangeValue(event.pos())      # get frame
            _helpers.gui.player.set_pause(True)                          # pause player while scrubbing
            _helpers.gui.gifPlayer.gif.setPaused(True)                   # pause GIF player while scrubbing

            # Handle dragging trim markers
            if self.grabbing_clamp_minimum:
                # Dragging START marker - update _helpers.gui.minimum
                new_min = min(frame, _helpers.gui.maximum - 1)  # Don't let START pass END
                _helpers.gui.minimum = max(0, new_min)  # Don't go below 0
                self.update()  # Repaint to show new marker position
            elif self.grabbing_clamp_maximum:
                # Dragging END marker - update _helpers.gui.maximum
                new_max = max(frame, _helpers.gui.minimum + 1)  # Don't let END pass START
                _helpers.gui.maximum = min(_helpers.gui.sliderProgress.maximum(), new_max)  # Don't go beyond video
                self.update()  # Repaint to show new marker position
            else:
                # Normal scrubbing - seek within trim range
                clamped_frame = min(_helpers.gui.maximum, max(_helpers.gui.minimum, frame))
                _helpers.gui.player.set_and_update_progress(clamped_frame, SetProgressContext.SCRUB)
            self.last_mouseover_time = 0                        # reset last mouseover time to stop drawing timestamp immediately
            self.scrubbing = True                               # mark that we're scrubbing


    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        ''' Unpauses the player after scrubbing, unless it was paused
            originally. Does not emit the `sliderReleased` signal. '''

        just_restarted = False
        frame = self.pixelPosToRangeValue(event.pos())          # get frame

        # Handle releasing trim markers
        if self.grabbing_clamp_minimum or self.grabbing_clamp_maximum:
            # Released trim marker - just clear the grab flags
            pass  # Marker already updated in mouseMoveEvent
        elif self.scrubbing:
            # Normal scrubbing
            if frame == _helpers.gui.frame_count:
                just_restarted = True
                _helpers.gui.restart()
            else:
                clamped_frame = min(_helpers.gui.maximum, max(_helpers.gui.minimum, frame))
                _helpers.gui.player.set_and_update_progress(clamped_frame, SetProgressContext.NAVIGATION_EXACT)

        if not just_restarted:                                  # do not touch pause state if we manually restarted
            if _helpers.gui.restarted:
                if _helpers.settings.checkNavigationUnpause.isChecked():
                    _helpers.gui.force_pause(False)                      # auto-unpause after restart
                    _helpers.gui.restarted = False
            else:
                paused = False or _helpers.gui.is_paused                 # stay paused if we were paused
                _helpers.gui.player.set_pause(paused)
                _helpers.gui.gifPlayer.gif.setPaused(paused)

        self.grabbing_clamp_minimum = False
        self.grabbing_clamp_maximum = False
        if self.underMouse():                                   # resume drawing timestamp after release
            self.last_mouseover_time = time.time()
        self.scrubbing = False


    def pixelPosToRangeValue(self, pos: QtCore.QPoint) -> int:  # https://stackoverflow.com/a/52690011
        ''' Auto-magically detects the correct value to set the handle
            to based on a given `pos`. Works with horizontal and vertical
            sliders, with or without stylesheets. '''
        try:
            opt = QtW.QStyleOptionSlider()
            self.initStyleOption(opt)

            groove_rect = self.style().subControlRect(QtW.QStyle.CC_Slider, opt, QtW.QStyle.SC_SliderGroove, self)
            handle_rect = self.style().subControlRect(QtW.QStyle.CC_Slider, opt, QtW.QStyle.SC_SliderHandle, self)
            try:
                raw_position = pos - handle_rect.center() + handle_rect.topLeft()
            except TypeError:                                   # event.pos() becomes None in rare, unknown circumstances
                pos = self.mapFromGlobal(QtGui.QCursor.pos())
                raw_position = pos - handle_rect.center() + handle_rect.topLeft()

            if self.orientation() == Qt.Horizontal:
                slider_min = groove_rect.x()
                slider_max = groove_rect.right() - handle_rect.width() + 1
                new_position = raw_position.x() - slider_min
            else:
                slider_min = groove_rect.y()
                slider_max = groove_rect.bottom() - handle_rect.height() + 1
                new_position = raw_position.y() - slider_min

            return QtW.QStyle.sliderValueFromPosition(
                self.minimum(),                                 # min
                self.maximum(),                                 # max
                new_position,                                   # position
                slider_max - slider_min,                        # span
                opt.upsideDown                                  # upsideDown
            )
        except:
            logger.warning(f'(!) Unexpected error in pixelPosToRangeValue - {format_exc()}')
            return 0                                            # return 0 as a failsafe


    def rangeValueToPixelPos(self, value: int) -> int:          # https://stackoverflow.com/a/52690011
        ''' Auto-magically detects the correct X/Y position to set the handle
            to based on a given `value`. Works with horizontal and vertical
            (...? see TODO below) sliders, with or without stylesheets. '''
        opt = QtW.QStyleOptionSlider()
        self.initStyleOption(opt)

        groove_rect = self.style().subControlRect(QtW.QStyle.CC_Slider, opt, QtW.QStyle.SC_SliderGroove, self)
        handle_rect = self.style().subControlRect(QtW.QStyle.CC_Slider, opt, QtW.QStyle.SC_SliderHandle, self)

        is_horizontal = self.orientation() == Qt.Horizontal
        if is_horizontal:
            slider_min = groove_rect.x()
            slider_max = groove_rect.right() - handle_rect.width() + 1
        else:
            slider_min = groove_rect.y()
            slider_max = groove_rect.bottom() - handle_rect.height() + 1

        raw_position = QtW.QStyle.sliderPositionFromValue(
            self.minimum(),                                     # min
            self.maximum(),                                     # max
            value,                                              # position
            slider_max - slider_min,                            # span
            opt.upsideDown                                      # upsideDown
        )

        # TODO test this on vertical
        if is_horizontal: return raw_position + handle_rect.center().x() - handle_rect.topLeft().x()
        else:             return raw_position + handle_rect.center().y() - handle_rect.topLeft().y()

