"""QVideoPlayer widget — main video display with crop and drag-drop support."""
from __future__ import annotations

import os
import time
import math
import logging
from traceback import format_exc

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets as QtW

from pyplayer import constants
from pyplayer.widgets.helpers import gui, app, cfg, settings
from pyplayer.widgets.player_backend import PyPlayerBackend


logger = logging.getLogger('widgets.py')


class QVideoPlayer(QtW.QWidget):    # https://python-camelot.s3.amazonaws.com/gpl/release/pyqt/doc/advanced/development.html <- relevant?
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setAttribute(Qt.WA_StyledBackground, True)     # https://stackoverflow.com/questions/7276330/qt-stylesheet-for-custom-widget
        self.setToolTipDuration(2000)
        self.setMouseTracking(True)                         # required for detecting idle movement
        self.setMinimumHeight(10)

        self.player = PyPlayerBackend(self)                 # NOTE: this is set purely so we can set global aliases in `main.pyw`
        self.players: dict[str, PyPlayerBackend] = {}

        self._text_position = 5
        self._text_height_percent = 0.05
        self._text_x_percent = 0.016
        self._text_y_percent = 0.016
        self._text_max_opacity = 255

        self.idle_timeout_time = 0.0
        self.last_invalid_snap_state_time = 0.0
        self.dragdrop_in_progress = False
        self.dragdrop_last_modifiers = None
        self.dragdrop_subtitle_count = 0
        self.dragdrop_is_folder = False
        self.dragdrop_files = []

        self.dragging: int = None                           # NOTE: 0 is valid -> always check against None
        self.dragging_offset: QtCore.QPoint = None
        self.drag_axis_lock: int = None
        self.panning = False
        self.true_left = 100
        self.true_right = 250
        self.true_top = 100
        self.true_bottom = 250
        self.true_rect: QtCore.QRect = None

        self.selection: list[QtCore.QPoint] = None
        self.last_factored_points: list[QtCore.QPoint] = None
        self.crop_frames: list[QtW.QFrame] = None
        self.crop_rect: QtCore.QRect = None
        self.reference_example: dict[int, dict[int]] = None
        self.text_y_offsets: dict[int, int] = None
        self.cursors = {
            0: QtGui.QCursor(Qt.SizeFDiagCursor),
            1: QtGui.QCursor(Qt.SizeBDiagCursor),
            2: QtGui.QCursor(Qt.SizeBDiagCursor),
            3: QtGui.QCursor(Qt.SizeFDiagCursor)
        }


    def reset_dragdrop_status(self):
        ''' Quickly clears drag-and-drop related messages and properties. '''
        gui.statusbar.clearMessage()
        self.player.show_text('')
        self.dragdrop_last_modifiers = None
        self.dragdrop_in_progress = False


    def reset_undermouse_state(self):
        ''' HACK: Manually updates `self.underMouse()` and
            immediately hides cursor if it's over the player. '''
        if app.widgetAt(QtGui.QCursor.pos()) is self:
            self.setAttribute(Qt.WA_UnderMouse, True)
            self.idle_timeout_time = 1.0                    # 0 locks the UI, so set it to 1
        else:
            self.setAttribute(Qt.WA_UnderMouse, False)
        self.update()


    # ---------------------
    # Cropping Utilities
    # ---------------------
    def get_crop_point_index_in_range(self, pos: QtCore.QPoint, _range: int = 30) -> int:
        ''' Returns the index of the closest crop-corner to `pos`,
            if any are within `_range` pixels, otherwise None. '''
        min_dist = 1000
        min_point = None
        for point in self.selection:
            #dist = abs(pos.x() - point.x()) + abs(pos.y() - point.y())     # TODO: verify that manhattanLength is actually better than this
            dist = (pos - point).manhattanLength()          # https://doc.qt.io/qt-5/qpoint.html#manhattanLength
            if dist < min_dist:
                min_dist = dist
                min_point = point
        return None if min_dist > _range else self.selection.index(min_point)


    def get_crop_edge_index_in_range(self, pos: QtCore.QPoint, _range: int = 15) -> int:
        ''' Returns the index of the closest crop-edge to `pos`, if
            any are within `_range` pixels, otherwise None. Indexes:
            Left: 0, Top: 1, Right: 2, Bottom: 3. '''
        s = self.selection
        for index in range(2):  # 0, 1
            if s[index].x() - _range <= pos.x() <= s[index].x() + _range and s[index].y() < pos.y() < s[(index + 2) % 4].y():
                return 0 if index == 0 else 2               # hovering over left edge if index == 0, else right edge
            elif s[index * 2].y() - _range <= pos.y() <= s[index * 2].y() + _range and s[index * 2].x() < pos.x() < s[(index * 2) + 1].x():
                return 1 if index == 0 else 3               # hovering over top edge if index == 0, else bottom edge
        return None


    def correct_points(self, changed_point_index: int):
        reference_point = self.selection[changed_point_index]
        x, y = reference_point.x(), reference_point.y()
        corrective_functions = self.reference_example[changed_point_index]
        for index, point in enumerate(self.selection):
            if index in corrective_functions:                                           # only 3/4 points are in each reference_example
                corrective_functions[index](x, y)                                       # run reference_example corrective function
                point.setX(min(self.true_right, max(self.true_left, point.x())))        # clamp each point to true borders
                point.setY(min(self.true_bottom, max(self.true_top, point.y())))        # true_bottom > true_top
                #self.selection[self.dragging].setX(min(self.true_right, max(self.true_left, point.x())))
                #self.selection[self.dragging].setY(min(self.true_bottom, max(self.true_top, point.y())))        # true_bottom > true_top
                #print('true borders (lrtb):', self.true_left, self.true_right, self.true_top, self.true_bottom, '| points:', point.x(), point.y(), f'| widget size: {self.width()}x{self.height()}')


    def factor_point(self, pos: QtCore.QPoint) -> QtCore.QPointF:
        ''' Converts a `QPoint` (`pos`) relative to `QVideoPlayer`'s viewport to
            a corresponding `QPointF` relative to the media's native resolution
            using the factor between the two. libVLC seemingly chooses to not
            expose these values, so we must calculate them manually. '''
        w = self.width()
        h = self.height()
        vw = gui.vwidth
        vh = gui.vheight
        ratio = vw / vh                     # native aspect ratio
        widget_ratio = w / h                # aspect ratio of QVideoPlayer
        if widget_ratio < ratio:            # video fills viewport width (there are black bars top/bottom)
            factor = vw / w
            void = ((h * factor) - vh) / 2  # calculate size of black bars
            x = pos.x() * factor
            y = (pos.y() * factor) - void   # account for black bars
            y = max(0, min(y, vh))          # I don't remember why this is needed
        else:                               # video fills viewport height (there are black bars left/right)
            factor = vh / h
            void = ((w * factor) - vw) / 2  # calculate size of black bars
            x = (pos.x() * factor) - void   # account for black bars
            y = pos.y() * factor
            x = max(0, min(x, vw))          # I don't remember why this is needed
        #print(f'factored pos ({pos.x()}, {pos.y()}) to ({x}, {y}) -> ratio={ratio} widget_ratio={widget_ratio} w={w} h={h} vw={vw} vh={vh} factor={factor} void={void}')
        return QtCore.QPointF(x, y)


    def defactor_point(self, pos: QtCore.QPointF) -> QtCore.QPoint:
        ''' The opposite of `self.factor_point()`: converts a `QPointF`
            (`pos`) relative to the media's native resolution to a
            corresponding `QPoint` relative to `QVideoPlayer`'s viewport. '''
        w = self.width()
        h = self.height()
        vw = gui.vwidth
        vh = gui.vheight
        ratio = vw / vh
        widget_ratio = w / h
        if widget_ratio < ratio:                            # video fills viewport width (there are black bars top/bottom)
            factor = vw / w
            void = ((h * factor) - vh) / 2                  # ((h - (w / video_ratio)) / 2)
            x = pos.x() / factor
            y = (pos.y() + void) / factor
            y = max(0, min(y, h))
        else:                                               # video fills viewport height (there are black bars left/right)
            factor = vh / h
            void = ((w * factor) - vw) / 2
            x = (pos.x() + void) / factor
            y = pos.y() / factor
            x = max(0, min(x, w))
        #print(f'de-factored pos ({pos.x()}, {pos.y()}) to ({x}, {y}) -> ratio={ratio} widget_ratio={widget_ratio} w={w} h={h} vw={vw} vh={vh} factor={factor} void={void}')
        return QtCore.QPoint(x, y)


    def find_true_borders(self):
        ''' Updates `self.true_rect` with a `QRect` containing the corners
            of the media's actual resolution within `QVideoPlayer`'s viewport.
            Also updates `self.true_{left/right/top/bottom}`. Similar to
            `self.factor_point()`/`self.defactor_point()`. I don't remember why,
            but a different calculation for the black bar was required here. '''
        w = self.width()
        h = self.height()

        # TODO which one is faster, vsize version or commented-out version? is having vsize JUST for this worth it?
        #vw = gui.vwidth
        #vh = gui.vheight
        #video_ratio = vw / vh                              # vh is never 0 (handled in gui.open())
        #widget_ratio = w / h
        #if widget_ratio < video_ratio:                     # video fills viewport width (there are black bars top/bottom)

        try:
            #if gui.gifPlayer._baseZoom == 1.0:
            #    expected_size = gui.vsize
            #    hvoid = (h - expected_size.height()) / 2
            #    wvoid = (w - expected_size.width()) / 2
            #    self.true_left =   int(wvoid)               # ensure potential error is outside bounds of actual video size
            #    self.true_right =  math.ceil(w - wvoid)     # ensure potential error is outside bounds of actual video size
            #    self.true_top =    int(hvoid)               # ensure potential error is outside bounds of actual video size
            #    self.true_bottom = math.ceil(h - hvoid)     # ensure potential error is outside bounds of actual video size
            #else:

            expected_size = gui.vsize.scaled(self.size(), Qt.KeepAspectRatio)
            if expected_size.height() < h:                  # video fills viewport width (there are black bars top/bottom)
                logger.debug('Video fills viewport width (there are black bars top/bottom)')
                #void = ((h - (w / video_ratio)) / 2)
                void = (h - expected_size.height()) / 2
                self.true_left =   0
                self.true_right =  w
                self.true_top =    int(void)                # ensure potential error is outside bounds of actual video size
                self.true_bottom = math.ceil(h - void)      # ensure potential error is outside bounds of actual video size
            else:                                           # video fills viewport height (there are black bars left/right)
                logger.debug('Video fills viewport height (there are black bars left/right)')
                #void = ((w - (h * video_ratio)) / 2)
                void = (w - expected_size.width()) / 2
                self.true_left =   int(void)                # ensure potential error is outside bounds of actual video size
                self.true_right =  math.ceil(w - void)      # ensure potential error is outside bounds of actual video size
                self.true_top =    0
                self.true_bottom = h

            logger.debug(f'void={void} w={w} h={h} expected_size={expected_size}')
            self.true_rect = QtCore.QRect(QtCore.QPoint(self.true_left, self.true_top), QtCore.QPoint(self.true_right, self.true_bottom))
        except:
            logger.debug(f'(!) find_true_borders failed: {format_exc()}')


    def update_crop_frames(self):
        ''' Updates the geometry for the four `QFrame`'s representing cropped
            out region. Updates the crop info panel accordingly. Saves current
            set of factored points for later use. '''
        selection = self.selection
        crop_top =    selection[0].y()                      # TODO make these @property?
        crop_left =   selection[0].x()
        crop_right =  selection[3].x()
        crop_bottom = selection[3].y()
        crop_height = crop_bottom - crop_top
        w = self.width()

        crop_frames = self.crop_frames
        crop_frames[0].setGeometry(0, 0, w, max(0, crop_top))                          # 0 top rectangle (full width)
        crop_frames[1].setGeometry(0, crop_top, crop_left, crop_height)                # 1 left rectangle
        crop_frames[2].setGeometry(crop_right, crop_top, w - crop_right, crop_height)  # 2 right rectangle
        crop_frames[3].setGeometry(0, crop_bottom, w, self.height() - crop_bottom)     # 3 bottom rectangle (full width)

        lfp = self.last_factored_points
        #if gui.gifPlayer._baseZoom == 1:
        #    lfp[0] = selection[0]
        #    lfp[1] = selection[1]
        #    lfp[2] = selection[2]
        #    lfp[3] = selection[3]
        #else:
        factor_point = self.factor_point
        lfp[0] = factor_point(selection[0])
        lfp[1] = factor_point(selection[1])
        lfp[2] = factor_point(selection[2])
        lfp[3] = factor_point(selection[3])

        # set crop info panel's strings
        gui.labelCropSize.setText(f'{lfp[1].x() - lfp[0].x():.0f}x{lfp[2].y() - lfp[0].y():.0f}')
        gui.labelCropTop.setText(f'T: {lfp[0].y():.0f}')
        gui.labelCropLeft.setText(f'L: {lfp[0].x():.0f}')
        gui.labelCropRight.setText(f'R: {lfp[3].x():.0f}')
        gui.labelCropBottom.setText(f'B: {lfp[3].y():.0f}')


    def refresh_crop_cursor(self, pos: QtCore.QPoint):
        ''' Updates the cursor to an appropriate resize/grab cursor
            based on its `pos` relative to the current crop region. '''
        cursor = app.overrideCursor()
        crop_point_index = self.get_crop_point_index_in_range(pos)
        edge_index = self.get_crop_edge_index_in_range(pos)
        if crop_point_index is not None:        # https://doc.qt.io/qt-5/qguiapplication.html#overrideCursor
            if cursor:     app.changeOverrideCursor(self.cursors[crop_point_index])
            else:          app.setOverrideCursor(self.cursors[crop_point_index])
        elif edge_index is not None:
            if edge_index % 2 == 0:
                if cursor: app.changeOverrideCursor(Qt.SizeHorCursor)
                else:      app.setOverrideCursor(Qt.SizeHorCursor)
            else:
                if cursor: app.changeOverrideCursor(Qt.SizeVerCursor)
                else:      app.setOverrideCursor(Qt.SizeVerCursor)
        elif self.crop_rect.contains(pos):
            if cursor:     app.changeOverrideCursor(Qt.SizeAllCursor)
            else:          app.setOverrideCursor(Qt.SizeAllCursor)
        elif cursor:
            app.restoreOverrideCursor()
            while app.overrideCursor():
                app.restoreOverrideCursor()


    # ---------------------
    # Events
    # ---------------------
    def paintEvent(self, event: QtGui.QPaintEvent):
        #super().paintEvent(event)                          # TODO this line isn't actually needed?
        if not gui.actionCrop.isChecked(): return           # nothing else to paint if we're not cropping

        s = self.selection
        white = QtGui.QColor(255, 255, 255)
        black = QtGui.QColor(0, 0, 0)

        p = QtGui.QPainter()
        p.begin(self)
        p.setPen(QtGui.QPen(white, 6, Qt.SolidLine))
        p.setBrush(white)
        p.setFont(QtGui.QFont('Segoe UI Light', 10))

        try:
            # draw thin border around video (+2 and -4 to account for size-6 pen)
            p.drawRect(s[0].x() + 2,
                       s[0].y() + 2,
                       s[1].x() - s[0].x() - 4,
                       s[2].y() - s[0].y() - 4)

            # draw handle and coordinates for each corner
            for index, point in enumerate(s):
                #p.drawRect(point.x() - 3, point.y() - 3, 5, 5)
                text = f'({self.last_factored_points[index].x():.0f}, {self.last_factored_points[index].y():.0f})'
                p.setPen(black)                                                              # set color to black
                p.drawText(point.x() + 1, point.y() + self.text_y_offsets[index] + 1, text)  # draw shadow first
                p.setPen(QtGui.QPen(white, 6, Qt.SolidLine))                                 # set color to white
                p.drawText(point.x(), point.y() + self.text_y_offsets[index], text)          # draw actual text over shadow
                p.drawPoint(point.x(), point.y())                                            # size-6 point to represent handles

        except: logger.warning(f'(!) Unexpected error while painting crop view from QVideoPlayer: {format_exc()}')
        finally: p.end()


    def resizeEvent(self, event: QtGui.QResizeEvent):
        ''' Recalculates borders and crop points while resizing if crop-mode
            is enabled. Also sets a timer for snapping the window to the
            current media's aspect ratio, as long as a timer isn't already
            active, snap-mode is enabled, we haven't recently altered the UI/
            maximized/fullscreened, and a file has already been loaded. '''
        if gui.actionCrop.isChecked():
            self.find_true_borders()
            #self.selection = [self.defactor_point(p) for p in self.last_factored_points]    # this should work but has bizarre side effects
            for index in range(4):
                self.correct_points(index)
            self.update_crop_frames()
        super().resizeEvent(event)

        # mark if we were recently fullscreen/maximized so we know not to snap-resize during the next few resizeEvents
        if gui.isMaximized() or gui.isFullScreen():
            self.last_invalid_snap_state_time = time.time()

        # set timer to resize window to fit player (if no file has been played yet, do not set timers on resize)
        # TODO: this does not work correctly on Linux!!! see `gui.timerEvent()` for more details
        elif (
            not gui.timer_id_resize_snap
            and time.time() - self.last_invalid_snap_state_time > 0.35
            and gui.first_video_fully_loaded
        ):
            gui.timer_id_resize_snap = gui.startTimer(200, Qt.CoarseTimer)

        self.player.on_resize(event)


    def mousePressEvent(self, event: QtGui.QMouseEvent):
        ''' Handles grabbing crop points/edges in crop-mode. Moves through the
            recent files list if the forwards/backwards buttons are pressed. '''
        try:
            if not gui.actionCrop.isChecked():                          # no crop -> check for back/forward buttons
                if event.button() == Qt.BackButton:      gui.cycle_recent_files(forward=False)
                elif event.button() == Qt.ForwardButton: gui.cycle_recent_files(forward=True)
                elif event.button() == Qt.MiddleButton:  gui.middle_click_player_actions[settings.comboPlayerMiddleClick.currentIndex()]()
                return  # TODO add back/forward functionality globally (not as easy as it sounds?)
            elif not event.button() == Qt.LeftButton:                   # ignore non-left-clicks in crop mode
                pos = self.mapFromGlobal(QtGui.QCursor.pos())
                return self.refresh_crop_cursor(pos)

            pos = self.mapFromGlobal(QtGui.QCursor.pos())               # mousePressEvent's event.pos() appears to return incorrect values...
            self.refresh_crop_cursor(pos)                               # ...in certain areas, leading to bad offsets and mismatched selections
            self.dragging = self.get_crop_point_index_in_range(pos)
            self.panning = False
            if self.dragging is not None:
                self.drag_axis_lock = None                              # reset axis lock before dragging corners
                self.dragging_offset = pos - self.selection[self.dragging]
            else:
                edge_index = self.get_crop_edge_index_in_range(pos)
                if edge_index is not None:
                    if edge_index % 2 == 0:
                        self.dragging = 0 if edge_index < 2 else 3
                        self.drag_axis_lock = 0
                    else:
                        self.dragging = 0 if edge_index < 2 else 3
                        self.drag_axis_lock = 1
                    self.dragging_offset = pos - self.selection[self.dragging]
                elif self.crop_rect.contains(pos):      # no corners/edges, but clicked inside crop rect -> panning
                    self.dragging = -1
                    self.drag_axis_lock = None          # reset axis lock before panning
                    self.dragging_offset = pos - self.selection[0]
                    if app.overrideCursor(): app.changeOverrideCursor(Qt.ClosedHandCursor)
                    else:                    app.setOverrideCursor(Qt.ClosedHandCursor)
            event.accept()
            self.update()
        except:
            logger.warning(f'(!) Unexpected error while clicking QVideoPlayer: {format_exc()}')
        return super().mousePressEvent(event)


    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        ''' Handles mouse movement over the player by resetting the idle timer
            if crop mode is disabled, or by allowing crop edges/corners (or the
            entire region) to be dragged around if crop mode is enabled. '''
        if not gui.actionCrop.isChecked():              # idle timeout is handled in QVideoSlider's paintEvent since it constantly updates
            if settings.checkHideIdleCursor.isChecked() and gui.video:
                self.idle_timeout_time = time.time() + settings.spinHideIdleCursorDuration.value()
            else:
                self.idle_timeout_time = 0.0            # 0 locks the cursor/UI
            return event.ignore()                       # only handle idle timeouts if we're not cropping

        # crop mode enabled -> lock UI and handle dragging and/or crop-cursor
        self.idle_timeout_time = 0.0
        try:
            pos = self.mapFromGlobal(event.globalPos())  # event.pos() does not work. I have no explanation.
            if self.dragging is None:
                self.refresh_crop_cursor(pos)

            elif event.buttons() == Qt.LeftButton:
                s = self.selection
                if self.drag_axis_lock is None: new_pos = pos - self.dragging_offset
                elif self.drag_axis_lock == 0:  new_pos = QtCore.QPoint((pos - self.dragging_offset).x(), s[self.dragging].y())  # x-axis only
                else:                           new_pos = QtCore.QPoint(s[self.dragging].x(), (pos - self.dragging_offset).y())  # y-axis only
                new_pos.setX(min(self.true_right, max(self.true_left, new_pos.x())))
                new_pos.setY(min(self.true_bottom, max(self.true_top, new_pos.y())))

                # we are panning the entire crop area
                if self.dragging == -1:
                    delta = new_pos - s[0]
                    for point in s:
                        point += delta

                    if not self.true_rect.contains(s[3]):
                        up =   QtCore.QPoint(0, 1)
                        left = QtCore.QPoint(1, 0)
                        while s[3].y() > self.true_bottom:
                            for point in s: point -= up
                        while s[3].x() > self.true_right:
                            for point in s: point -= left
                    self.panning = True                 # indicate that we're panning so we don't pause on release

                # we are dragging a corner/edge
                else:
                    # holding ctrl -> maintain square crop region
                    if app.keyboardModifiers() & Qt.ControlModifier:    # TODO this barely works, but it works. for now
                        self.dragging = 0                               # TODO bandaid fix so I don't have to finish all 4 points
                        new_x = new_pos.x()
                        anchor_index = (self.dragging + 1) % 4
                        anchor = s[anchor_index]
                        dragged = s[self.dragging]
                        if self.dragging % 2 == 0:
                            new_y = dragged.y() + (new_x - dragged.x())
                            dragged.setY(new_y)
                            height = s[(self.dragging + 2) % 4].y() - dragged.y()
                            anchor.setX(new_x + height)  # new_x - height is close to making indexes 1/3 work
                        else:
                            new_y = dragged.y() - (new_x - dragged.x())
                            dragged.setY(new_y)
                            height = s[(self.dragging + 2) % 4].y() - dragged.y()
                            anchor.setX(new_x - height)  # new_x - height is close to making indexes 1/3 work
                        ##dragged.setY(anchor.x() - dragged.x())
                        dragged.setX(new_x)
                        #dragged.setY(new_x)
                        #anchor.setX(anchor.x() - (anchor.x() - dragged.x()))
                        #height = s[(self.dragging + 2) % 4].y() - dragged.y()
                        #anchor.setX(new_x + height)    # new_x - height is close to making indexes 1/3 work
                        self.correct_points(self.dragging)
                        self.correct_points(anchor_index)
                    else:
                        s[self.dragging] = new_pos
                        self.correct_points(self.dragging)

                self.crop_rect.setTopLeft(s[0])
                self.crop_rect.setBottomRight(s[3])

                self.update_crop_frames()               # update crop frames and factored points
                self.repaint()                          # repaint QVideoPlayer (TODO: update() vs repaint() here)

        except TypeError: pass                          # self.dragging is None
        except: logger.warning(f'(!) Unexpected error while dragging crop points: {format_exc()}')
        #return super().mouseMoveEvent(event)           # TODO: required for mouseReleaseEvent to work properly?


    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        ''' Pauses media after clicking and releasing left-click over player,
            ignoring clicks that were dragged outside player. Releases dragged
            crop points/edges if needed, and resets cursor. '''

        # ensure we're actually over the player still and we're not panning/dragging a crop region
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()) and not self.panning:
            if (self.dragging is None and not gui.actionCrop.isChecked()) or self.dragging == -1:
                gui.pause()

        # right-click released -> prepare cursor/properties for context menu if necessary
        if event.button() == Qt.RightButton:
            # NOTE: this event happens before contextMenuEvent, which might not fire at all.
            # -> use a timer so contextMenuEvent has a chance to see the flag is set while...
            # ...guaranteeing the flag gets reset even if contextMenuEvent never fires
            if gui.ignore_next_right_click:             # not actually opening context menu
                def reset():
                    gui.ignore_next_right_click = False
                QtCore.QTimer.singleShot(50, Qt.CoarseTimer, reset)
            else:
                self.setCursor(Qt.ArrowCursor)          # HACK: reset base cursor as well to...
                self.unsetCursor()                      # ...fix obscure drag-and-drop cursor bugs
                while app.overrideCursor():
                    app.restoreOverrideCursor()

        # left-click released and we're not dragging the crop region/points/edges
        elif self.dragging is not None:                 # refresh crop cursor if we were just dragging
            self.refresh_crop_cursor(self.mapFromGlobal(event.globalPos()))

        #self.panning = False
        self.dragging = None                            # release crop-drag


    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        ''' Triggers user's desired double-click
            action after double-clicking the player. '''
        if event.button() == Qt.LeftButton:
            index = settings.comboPlayerDoubleClick.currentIndex()
            gui.double_click_player_actions[index]()


    def leaveEvent(self, event: QtCore.QEvent):
        ''' Automatically stop dragging, reset the cursor, and
            lock the cursor/UI when the mouse leaves the player. '''
        self.idle_timeout_time = 0.0                    # 0 locks the cursor/UI

        # HACK: set base cursors for the widgets above/below the player...
        # ...to fix various obscure cursor bugs related to drag-and-drop
        gui.dockControls.setCursor(Qt.ArrowCursor)      # (these are unset in their `enterEvent`s)
        gui.menubar.setCursor(Qt.ArrowCursor)

        # if cropping & the mouse is still over the player but NOT the controls (in fullscreen),...
        # ...don't reset cursor (the player AND each crop frame trigger their own `leaveEvent`'s)
        should_reset = True
        if gui.actionCrop.isChecked():
            mouse_pos = QtGui.QCursor.pos()
            if self.rect().contains(self.mapFromGlobal(mouse_pos)):
                control_pos = gui.dockControls.mapFromGlobal(mouse_pos)
                if not gui.dockControls.rect().contains(control_pos):
                    should_reset = False

        # we did not meet the specific scenario above
        if should_reset:
            while app.overrideCursor():                 # reset cursor to default
                app.restoreOverrideCursor()

        self.dragging = None                            # release crop-drag
        #print('setting panning to true', event.buttons())
        #self.panning = True  # TODO this is a bandaid fix. dragging/panning sometimes wrongly report as None and False, causing unexpected pauses in mouseReleaseEvent


    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        ''' Accepts a cursor-drag if files are being dragged.
            NOTE: Requires `self.setAcceptDrops(True)`. '''
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()
        self.dragdrop_in_progress = True
        self.dragdrop_subtitle_count = 0
        self.dragdrop_is_folder = False

        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.dragdrop_files = files
        for file in files:
            if os.path.splitext(file)[-1] in constants.SUBTITLE_EXTENSIONS:
                self.dragdrop_subtitle_count += 1
            elif os.path.isdir(file):
                self.dragdrop_is_folder = True
                break

        return super().dragEnterEvent(event)            # run QWidget's built-in behavior


    def dragLeaveEvent(self, event: QtGui.QDragLeaveEvent):
        ''' Resets drag-and-drop status if user drags
            cursor off the window (to clear messages). '''
        self.reset_dragdrop_status()
        return super().dragLeaveEvent(event)


    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        ''' Indicates on the statusbar and player (if possible) what the current
            button-combination will do once the drag-and-drop finishes. Keeps
            track of combination to avoid repeated statusbar/marquee calls. '''
        files = self.dragdrop_files

        if self.dragdrop_is_folder:
            mod = event.keyboardModifiers()
            if mod != self.dragdrop_last_modifiers:     # VVV alt OR ctrl+shift (play random file without autoplay)
                if mod & Qt.AltModifier or (mod & Qt.ControlModifier and mod & Qt.ShiftModifier):
                    msg = 'Drop to select random media from folder (without shuffle mode)'
                elif mod & Qt.ControlModifier:          # ctrl only (play random file with autoplay (in shuffle mode))
                    msg = 'Drop to select random media from folder (with shuffle mode)'
                elif mod & Qt.ShiftModifier:            # shift only (play first file without autoplay)
                    msg = 'Drop to select first media file in folder (without autoplay)'
                else:                                   # no modifiers (play first file with autoplay)
                    msg = 'Drop to autoplay folder contents, or hold ctrl/alt/shift for more options'
            gui.statusbar.showMessage(msg, 0)
            self.player.show_text(msg, timeout=0, position=0)
        elif self.dragdrop_subtitle_count:
            count = self.dragdrop_subtitle_count
            if count == len(files):
                if gui.video:
                    if count == 1: msg = 'Drop to add subtitle file'
                    else:          msg = 'Drop to add subtitle files'
                else:
                    msg = 'You cannot drop subtitle files by themselves if no media is playing.'
            else:
                if count == 1: msg = 'Drop to play media and add subtitle file'
                else:          msg = 'Drop to play media and add subtitle files'
            gui.statusbar.showMessage(msg, 0)
            self.player.show_text(msg, timeout=0, position=0)
        elif not gui.video:                             # no media playing, can't show marquee. don't bother with special options
            gui.statusbar.showMessage('Drop to play media, or hold ctrl/alt/shift while media is playing for additional options')
        else:
            mod = event.keyboardModifiers()
            if mod != self.dragdrop_last_modifiers:
                self.dragdrop_last_modifiers = mod
                if mod & Qt.ControlModifier:            # ctrl (concat before current)
                    if len(files) == 1: msg = 'Drop to concatenate 1 file before current media'
                    else:               msg = f'Drop to concatenate {len(files)} files before current media'
                elif mod & Qt.AltModifier:              # alt (concat after current)
                    if len(files) == 1: msg = 'Drop to concatenate 1 file after current media'
                    else:               msg = f'Drop to concatenate {len(files)} files after current media'
                elif mod & Qt.ShiftModifier:            # shift (add audio track)
                    if len(files) == 1: msg = 'Drop to add as audio track'
                    else:               msg = 'Drop to add first file as audio track'
                    if os.path.abspath(files[0]) == gui.video:
                        msg += ' (disabled due to identical file)'
                else:
                    msg = 'Drop to play media, or hold ctrl/alt/shift for more options'
                gui.statusbar.showMessage(msg, 0)
                self.player.show_text(msg, timeout=0, position=0)
        return super().dragMoveEvent(event)


    def dropEvent(self, event: QtGui.QDropEvent):       # attempt to open dropped files
        ''' Attempts to open dropped files as either media or subtitle tracks.
            Only uses the first dropped file for opening media or folders.

            Allows modifiers to alter the interaction used:
            - No modifiers -> Opens single media file/adds subtitle track(s).
            - Ctrl         -> Adds single media file as an audio track.
            - Shift        -> Concatenates media file(s) to the end of the current media.
            - Alt          -> Concatenates media file(s) to the start of the current media. '''

        # clear messages
        self.reset_dragdrop_status()

        # HACK: reset base cursor to help fix several cursor bugs
        self.setCursor(Qt.ArrowCursor)
        self.unsetCursor()

        files = self.dragdrop_files
        if gui.isFullScreen():  focus_window = settings.checkFocusOnDropFullscreen.isChecked()
        elif gui.isMaximized(): focus_window = settings.checkFocusOnDropMaximized.isChecked()
        else:                   focus_window = settings.checkFocusOnDropNormal.isChecked()

        def open_media_and_add_subtitles():
            for file in files:                          # open first valid media file, if any
                if os.path.splitext(file)[-1] not in constants.SUBTITLE_EXTENSIONS:
                    if gui.open(file, focus_window=focus_window) == 1:
                        break
            if gui.video and self.dragdrop_subtitle_count:
                for file in files:                      # re-loop and add all valid subtitle files (if ANY media is playing)
                    if os.path.splitext(file)[-1] in constants.SUBTITLE_EXTENSIONS:
                        gui.add_subtitle_files(file)

        if self.dragdrop_is_folder:
            gui.open_folder(files[0], event.keyboardModifiers(), focus_window=focus_window)
        elif gui.video:
            mod = event.keyboardModifiers()
            if mod & Qt.ControlModifier:                # ctrl (concat before current)
                gui.concatenate_signal.emit(gui.actionCatBeforeThis, files)
            elif mod & Qt.AltModifier:                  # alt (concat after current)
                gui.concatenate_signal.emit(gui.actionCatAfterThis, files)
            elif mod & Qt.ShiftModifier:                # shift (add audio track, one file at time currently)
                file = files[0]
                if os.path.abspath(file) != gui.video: gui.add_audio(path=file)
                else: gui.statusbar.showMessage('Cannot add file to itself as an audio track', 10000)
            else:                                       # no modifiers pressed, add first media file and any subtitle files
                open_media_and_add_subtitles()
        else:
            open_media_and_add_subtitles()              # no media playing -> ignore modifiers entirely

        if settings.checkRememberDropFolder.isChecked():                # update `cfg.lastdir` if desired
            cfg.lastdir = files[0] if os.path.isdir(files[0]) else os.path.dirname(files[0])
        return super().dropEvent(event)                 # run QWidget's built-in behavior

