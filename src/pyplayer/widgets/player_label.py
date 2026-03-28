"""QVideoPlayerLabel — image/GIF display widget with zoom support."""
from __future__ import annotations

import math
import logging
from traceback import format_exc

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets as QtW

from pyplayer.widgets.helpers import gui, app, cfg, settings


logger = logging.getLogger('widgets.py')


class QVideoPlayerLabel(QtW.QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setMouseTracking(True)                     # needed so mouseMoveEvent works w/o clicking (needed for crop cursors)
        self.art = QtGui.QPixmap()
        self.gif = QtGui.QMovie()

        self._imageScale = 0                            # NOTE: scales are first set in qtstart.after_show_setup()
        self._artScale = 0
        self._gifScale = 0
        self._dragging = False
        self._draggingOffset = QtCore.QPoint()          # offset between cursor and image's real pos
        self.pixmapPos = QtCore.QPoint()                # local position of currently drawn QPixmap
        self.gifSize = QtCore.QSize()                   # gif's native size (not tracked by QMovie)
        self.gif.setCacheMode(QtGui.QMovie.CacheAll)    # required for jumpToFrame to work
        self.isCoverArt = False
        self.filename = None

        self.zoom = 1.0                                 # the true, current zoom level
        self._baseZoom = 1.0                            # base zoom level for the current window size based on zoom settings
        self._fitZoom = 1.0                             # the zoom required for fit mode, regardless of current zoom settings
        self._targetZoom = 1.0                          # the zoom level we're trying to reach while smooth-zooming
        self._smoothZoomTimerID = None                  # the ID for the smooth zoom timer, if any
        self._smoothZoomPos = QtCore.QPoint()           # the pos a smooth zoom should zoom in on
        self._smoothZoomFactor = 0.33                   # the "speed" at which a smooth zoom occurs
        self.zoomed = False                             # whether or not zoom-mode is enabled


    def play(self, file: str | bytes | None, interactable: bool = True, gif: bool = False, coverart: bool = False, autostart: bool = True):
        ''' Opens an image `file`, allowing image manipulation if `interactable`
            is True. Opens as a `QMovie` if `gif` is True (`QPixmap` otherwise),
            playing automatically if `autostart` is True. Sets `self.isCoverArt`
            to `coverart`. If `file` is None, the label is cleared and
            interaction is auto-disabled. '''

        # TODO: the `coverart` and `enabled` parameters used to be auto-determined based on whether or not `files`...
        # ...was bytes (if bytes, then it's cover art and we disable the widget). should we go back to that?
        self.gif.stop()
        self.filename = file
        self.zoomed = False
        if file is None:
            self.clear()
            self.gif.setFileName('')
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            return self.setEnabled(False)

        if gif:
            self.clear()
            self.gif.setFileName(file)
            if self.gif.frameCount() > 1:   # only treat GIF as animated if it has more than 1 frame
                try:                        # open gif in PIL to get its native size (fast)
                    with get_PIL_Image().open(file) as image:
                        size = image.size
                        self.gifSize.setWidth(size[0])
                        self.gifSize.setHeight(size[1])
                except:
                    self.gifSize = self.gif.frameRect().size()

                if self._gifScale == ZOOM_FIT:
                    self._resizeMovieFit()
                self.setMovie(self.gif)
                if autostart:
                    self.gif.start()
                logger.info('Animated GIF detected.')
            else:
                self.art.load(file)
                self.setPixmap(self.art)
                logger.info('Static GIF detected.')
        else:                               # static image. if `file` is bytes, it's cover art
            if isinstance(file, bytes):
                self.art.loadFromData(file)
            else:
                self.art.load(file)

            self.isCoverArt = coverart
            self.setPixmap(self.art)
            logger.info(f'Static image/cover art detected. (zoom={self.zoom})')

        self.disableZoom()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not interactable)
        self.setEnabled(interactable)


    def _updateImageScale(self, index: int, force: bool = False):
        ''' Updates the scaling mode for images (including
            single-frame GIFs, but excluding cover art). '''
        if not gui.actionCrop.isChecked() or force:
            logger.debug(f'Updating image scale to mode {index}')
            self._imageScale = index
            if self.pixmap():
                if not self.zoomed:
                    self._calculateBaseZoom()
                self.update()


    def _updateArtScale(self, index: int, force: bool = False):
        ''' Updates the scaling mode specifically for cover art. '''
        if not gui.actionCrop.isChecked() or force:
            logger.debug(f'Updating cover art scale to mode {index}')
            self._artScale = index
            if self.pixmap():
                if not self.zoomed:
                    self._calculateBaseZoom()
                self.update()


    def _updateGifScale(self, index: int, force: bool = False):
        ''' Updates the scaling mode for animated GIFs. '''
        if not gui.actionCrop.isChecked() or force:
            logger.debug(f'Updating gif scale to mode {index}')
            self._gifScale = index + 1      # FIXME: +1 is temporary until gifs properly support dynamic fit
            if self.movie():                # FIXME: ^^^ this is set manually in qtstart!!!!!
                if self.zoomed:             # FIXME: ^^^ it's also set in main.set_crop_mode!!!!
                    self.setZoom(self.zoom, force=True)
                else:
                    self._resetMovieSize()
                    self._calculateBaseZoom()


    def _updateSmoothZoomFactor(self, factor: int):
        ''' Updates the smooth zoom "speed" `factor / 100`. The `QSpinBox`
            is a percentage from 0-100 to make it easier to understand. '''
        self._smoothZoomFactor = factor / 100


    def _updatePreciseZoom(self, checked: bool):
        ''' Updates the "precise zoom" mode by swapping `pixmapPos`'s type
            between `QPoint` and `QPointF` to minimize errors. Precise zooming
            uses `QPointF`, normal zooming uses `QPoint`. '''
        if checked:
            if isinstance(self.pixmapPos, QtCore.QPoint):
                self.pixmapPos = QtCore.QPointF(self.pixmapPos)
        elif isinstance(self.pixmapPos, QtCore.QPointF):
            self.pixmapPos = self.pixmapPos.toPoint()


    def _resetMovieCache(self):
        ''' Stops and resets GIF to clear cached frames.
            Pause state is restored after reset. '''
        self.gif.stop()
        self.gif.setFileName(self.gif.fileName())
        self.gif.start()
        self.gif.setPaused(gui.is_paused)


    def _resetMovieSize(self):
        scale = self._gifScale
        self.setScaledContents(scale == ZOOM_FILL)
        if scale == ZOOM_NO_SCALING:
            self.gif.setScaledSize(QtCore.QSize(-1, -1))
        elif scale == ZOOM_FIT or self.width() < gui.vwidth or self.height() < gui.vheight:
            self._resizeMovieFit()
        elif scale == ZOOM_FILL:
            self.gif.setScaledSize(self.size())

        # TODO: the main issue with dynamic fit on gifs is that they start playing BEFORE we can actually see their true dimensions
        #       the fix appears to be something like loading the gif as a pixmap first, taking the dimensions, then playing as a gif
        #print('before', self.width(), self.height(), gui.vwidth, gui.vheight, self.gif.scaledSize().width(), self.gif.scaledSize().height())
        #if scale == ZOOM_FIT or self.width() < gui.vwidth or self.height() < gui.vheight: self._resizeMovieFit()
        #elif scale == ZOOM_FILL: self.gif.setScaledSize(self.size())
        #else: self.gif.setScaledSize(QtCore.QSize(-1, -1))
        self._resetMovieCache()


    def _resizeMovieFit(self):
        QtCore.QSize()
        self.gif.setScaledSize(self.gifSize.scaled(self.size(), Qt.KeepAspectRatio))


    def _calculateBaseZoom(self) -> float:
        ''' Calculates the default zoom level and minimum zoom level
            required to fit media within the current window size. '''

        # animated gif
        if self.movie():
            fitZoom = round(self.gif.scaledSize().width() / self.gifSize.width(), 4)
            scale = self._gifScale
            if scale == ZOOM_NO_SCALING:
                zoom = 1.0
            elif scale == ZOOM_FILL:
                w = self.width()
                h = self.height()
                vw = self.gifSize.width()
                vh = self.gifSize.height()
                ratio = vw / vh             # native gif aspect ratio
                widget_ratio = w / h        # aspect ratio of QVideoPlayerLabel
                if widget_ratio < ratio:    # gif is stretched vertically (there would be black bars top/bottom)
                    zoom = round(h / vh, 4)
                else:                       # gif is stretched horizontally (there would be black bars left/right)
                    zoom = round(w / vw, 4)
            else:                           # ZOOM_DYNAMIC_FIT (fit if media is smaller than window)
                zoom = fitZoom

        # image/cover art
        elif self.pixmap():
            fitSize = self.art.size().scaled(self.size(), Qt.KeepAspectRatio)
            fitZoom = round(fitSize.width() / self.art.width(), 4)

            scale = self._artScale if self.isCoverArt else self._imageScale
            if scale == ZOOM_FILL:
                w = self.width()
                h = self.height()
                vw = self.art.width()
                vh = self.art.height()
                ratio = vw / vh             # native image aspect ratio
                widget_ratio = w / h        # aspect ratio of QVideoPlayerLabel
                if widget_ratio < ratio:    # image is stretched vertically (there would be black bars top/bottom)
                    zoom = round(h / vh, 4)
                else:                       # image is stretched horizontally (there would be black bars left/right)
                    zoom = round(w / vw, 4)
            elif scale == ZOOM_FIT or self.width() < self.art.width() or self.height() < self.art.height():
                zoom = fitZoom
            else:                           # ZOOM_DYNAMIC_FIT (fit if image is smaller than window)
                zoom = 1.0

        # invalid mime-type, don't worry about zoom levels
        else:
            return 1.0

        self.zoom = self._baseZoom = self._targetZoom = zoom
        self._fitZoom = fitZoom
        return zoom


    def setZoom(
        self,
        zoom: float,
        pos: QtCore.QPoint = None,
        globalPos: QtCore.QPoint = None,
        force: bool = False,
        _smooth: bool = False
    ) -> float:

        is_gif = bool(self.movie())
        maxZoom = 100.0 if not is_gif else 20.0
        minZoomFactor = settings.spinZoomMinimumFactor.value()
        minZoom = self._baseZoom * minZoomFactor
        if settings.checkZoomForceMinimum.isChecked():
            minZoom = min(minZoomFactor, minZoom)

        if not _smooth:
            zoom = round(min(maxZoom, max(minZoom, zoom)), 4)
        if zoom == self.zoom and not force:
            if minZoomFactor == 1.0 and zoom == self._baseZoom and settings.checkZoomAutoDisable1x.isChecked():
                return self.disableZoom()   # _baseZoom == _targetZoom -> faster reset during smooth zoom (not worth it)
            return zoom

        willSmooth = not _smooth and settings.checkZoomSmooth.isChecked()
        if willSmooth:                      # about to start smoothing -> do first zoom-step now, start timer
            self._targetZoom = zoom
            if self._smoothZoomTimerID is None:
                zoom += (zoom - self.zoom) * self._smoothZoomFactor
                self._smoothZoomTimerID = self.startTimer(17, Qt.PreciseTimer)          # 17ms timer ~= 59fps

        if is_gif:
            if not willSmooth:
                if self._gifScale == ZOOM_FILL:
                    self.setScaledContents(False)
                    newSize = self.size().scaled(self.gifSize, Qt.KeepAspectRatio) * zoom
                else:
                    newSize = self.gifSize * zoom
                self.gif.setScaledSize(newSize)
                self._resetMovieCache()     # you can smooth zoom without freezing, but it's SLOWER than spam-resetting
        else:
            if globalPos:
                pos = self.mapFromGlobal(globalPos)
            if pos:
                if willSmooth:
                    self._smoothZoomPos = pos                   # set pos for smooth zoom to re-use
                elif settings.checkZoomPrecise.isChecked():
                    newSize = QtCore.QSizeF(self.art.size()) * zoom
                    oldSize = QtCore.QSizeF(self.art.size()) * self.zoom
                    oldPos = self.pixmapPos
                    xOffset = ((pos.x() - oldPos.x()) / oldSize.width()) * newSize.width()
                    yOffset = ((pos.y() - oldPos.y()) / oldSize.height()) * newSize.height()
                    self.pixmapPos = pos - QtCore.QPointF(xOffset, yOffset)
                    if not _smooth:                             # drag + zoom is bad unless it's a smooth zoom
                        self._draggingOffset = pos - self.pixmapPos
                else:
                    newSize = self.art.size() * zoom
                    oldSize = self.art.size() * self.zoom
                    oldPos = self.pixmapPos
                    xOffset = ((pos.x() - oldPos.x()) / oldSize.width()) * newSize.width()
                    yOffset = ((pos.y() - oldPos.y()) / oldSize.height()) * newSize.height()
                    self.pixmapPos = pos - QtCore.QPoint(xOffset, yOffset)
                    if not _smooth:                             # drag + zoom is bad unless it's a smooth zoom
                        self._draggingOffset = pos - self.pixmapPos

        if not willSmooth:
            self.zoom = zoom
        self.zoomed = True
        self.update()

        if not _smooth:
            logger.debug(f'QVideoPlayerLabel zoom set to {zoom} (pos={pos} | globalPos={globalPos})')
        return zoom


    def incrementZoom(
        self,
        increment: float,
        pos: QtCore.QPoint = None,
        globalPos: QtCore.QPoint = None,
        force: bool = False
    ) -> float:
        return self.setZoom(self.zoom + increment, pos, globalPos, force)


    def disableZoom(self) -> float:
        self.zoomed = False
        self.pixmapPos = self.rect().center() - self.art.rect().center()

        if self._smoothZoomTimerID: self._smoothZoomTimerID = self.killTimer(self._smoothZoomTimerID)
        if self.movie(): self._resetMovieSize()
        else: self.setScaledContents(False)

        self.update()
        return self._calculateBaseZoom()


    def pan(self, direction: QtCore.QPoint, mod: int = None):
        ''' Pans `self.pixmapPos` in `direction`, using `mod` modifiers. If
            `Shift` is held down, `direction` is transposed. If `Alt` is held
            down, `direction` is tripled. '''
        if mod is None:
            mod = app.keyboardModifiers()
        offset = direction

        # shift held -> scroll horizontally, alt held -> scroll 3x as far
        if mod & Qt.ShiftModifier:
            offset = offset.transposed()
        if mod & Qt.AltModifier:
            gui.ignore_next_alt = True
            offset = direction.transposed() * 3.0               # alt swaps horizontal/vertical scroll for some reason
        if settings.checkZoomPanInvertScroll.isChecked():
            offset *= -1

        self.pixmapPos += offset
        self.zoomed = True
        self.update()


    def mousePressEvent(self, event: QtGui.QMouseEvent):
        ''' Sets the offset between the cursor
            and our `QPixmap`'s local position. '''
        if event.button() == Qt.LeftButton and not gui.actionCrop.isChecked():
            self._draggingOffset = event.pos() - self.pixmapPos
        return super().mousePressEvent(event)                   # QLabel will pass event to underlying widgets (needed for cropping)


    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        ''' Handles mouse movement over the image player. Drags our `QPixmap` by
            adjusting its position based on the cursor's position relative to
            the offset we set in `mousePressEvent`, and resets the idle timer
            if crop mode is disabled. Otherwise, `QVideoPlayer.mouseMoveEvent()`
            is called to handle cropping. '''
        if not gui.actionCrop.isChecked():
            if event.buttons() == Qt.LeftButton:                # why doesn't `event.button()` work here?
                self.pixmapPos = event.pos() - self._draggingOffset
                self._dragging = True
                self.update()                                   # manually update
            if settings.checkHideIdleCursor.isChecked() and gui.video:
                gui.vlc.idle_timeout_time = time.time() + settings.spinHideIdleCursorDuration.value()
            else:
                gui.vlc.idle_timeout_time = 0.0                 # 0 locks the cursor/UI
        else:
            return super().mouseMoveEvent(event)                # QLabel will pass event to underlying widgets (needed for cropping)


    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        ''' Disables drag-mode on releasing a mouse button. If left-clicking
            and drag-mode was never enabled, then zoom-mode is disabled. '''
        if event.button() == Qt.LeftButton:
            if not (self.movie() or self._dragging):            # reset QVideoPlayerLabel's zoom if we click without dragging
                self.disableZoom()
        self._dragging = False
        return super().mouseReleaseEvent(event)                 # QLabel will pass event to underlying widgets (needed for cropping)


    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        if self.zoomed and event.button() == Qt.LeftButton: self.disableZoom()
        else: super().mouseDoubleClickEvent(event)


    def wheelEvent(self, event: QtGui.QWheelEvent):
        ''' Increments the zoom factor or pans `self.pixmapPos` depending
            on what modifiers and mouse buttons are held down. '''
        event.accept()                                          # accept event or QLabel will pass it through no matter what
        if gui.actionCrop.isChecked() or not gui.video: return

        # see if we want the secondary action and what our secondary action is
        mod = event.modifiers()
        secondary_pans = not settings.checkZoomPanByDefault.isChecked()
        if event.buttons() == Qt.RightButton:
            use_secondary = True
            gui.ignore_next_right_click = True
        else:
            use_secondary = mod & Qt.ControlModifier

        # pan the media around instead of zooming if desired
        if (use_secondary and secondary_pans) or (not use_secondary and not secondary_pans):
            return self.pan(event.angleDelta(), mod)

        # otherwise, calculate the factor with which to change our zoom
        add = event.angleDelta().y() > 0
        if mod & Qt.ShiftModifier:
            factor = settings.spinZoomIncrement3.value()    # shift -> #3
        elif mod & Qt.AltModifier:
            factor = settings.spinZoomIncrement2.value()    # alt -> #2
            add = event.angleDelta().x() > 0                # alt swaps horizontal/vertical scroll for some reason
            gui.ignore_next_alt = True
        else:
            factor = settings.spinZoomIncrement1.value()    # default -> #1

        # calculate and apply our new zoom level
        zoom = self._targetZoom if settings.checkZoomSmooth.isChecked() else self.zoom
        increment = (zoom / factor)
        self.setZoom(zoom + (increment if add else -increment), globalPos=QtGui.QCursor.pos())


    def resizeEvent(self, event: QtGui.QResizeEvent):
        ''' Scales the GIF/image/art while resizing, and calculates
            what zoom factor the new player size should start from. '''
        if self.hasScaledContents():
            return
        elif not self.zoomed:
            if self.pixmap():
                self._calculateBaseZoom()
            elif self.movie():
                if self._gifScale == ZOOM_FIT:
                    self._resizeMovieFit()
                self._resetMovieCache()
                self._calculateBaseZoom()
        elif self._gifScale == ZOOM_FILL:
            self.gif.setScaledSize(self.size().scaled(self.gifSize, Qt.KeepAspectRatio) * self.zoom)
            self._resetMovieCache()


    def timerEvent(self, event: QtCore.QTimerEvent):            # TODO why is zooming out so slow at lower smoothZoomFactors??
        if self._smoothZoomTimerID is not None:
            currentZoom = self.zoom
            if self._targetZoom == currentZoom:
                self._smoothZoomTimerID = self.killTimer(self._smoothZoomTimerID)
                self.setZoom(self._targetZoom, pos=self._smoothZoomPos, _smooth=True)
                #if self.movie(): self._resetMovieCache()       # only reset gif cache after smooth zoom is finished
            else:
                digits = 4 - (int(math.log10(self._targetZoom)) + 1)                        # smaller zoom, round to more digits
                newZoom = round(currentZoom + (self._targetZoom - currentZoom) * self._smoothZoomFactor, digits)
                if newZoom == currentZoom:
                    newZoom = self._targetZoom
                self.setZoom(newZoom, pos=self._smoothZoomPos, _smooth=True)
        return super().timerEvent(event)


    def paintEvent(self, event: QtGui.QPaintEvent):             # TODO very close to figuring out how to handle GIFs in here
        #if True:
        if self.pixmap():
            painter = QtGui.QPainter(self)
            if settings.checkScaleFiltering.isChecked():
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                transformMode = Qt.SmoothTransformation
            else:
                transformMode = Qt.FastTransformation

            # draw zoomed pixmap by using scale mode and the current zoom to generate new size
            scale = self._artScale if self.isCoverArt else self._imageScale
            #pixmap = self.art if self.pixmap() else self.gif.currentPixmap()
            pixmap = self.art
            if self.zoomed:
                zoom = self.zoom

                # at >1 zoom, drawing to QRect is MUCH faster and looks identical to art.scaled()
                try:
                    if zoom >= 1:
                        if settings.checkZoomPrecise.isChecked():
                            if scale != ZOOM_FILL: size = QtCore.QSizeF(pixmap.size())  # TODO V does this deform the image while zooming?
                            else:                  size = QtCore.QSizeF(self.size().scaled(pixmap.size(), Qt.KeepAspectRatio))
                            painter.drawPixmap(QtCore.QRectF(self.pixmapPos, size * zoom).toRect(), pixmap)
                        else:
                            if scale != ZOOM_FILL: size = pixmap.size()                 # TODO V ditto?
                            else:                  size = self.size().scaled(pixmap.size(), Qt.KeepAspectRatio)
                            painter.drawPixmap(QtCore.QRect(self.pixmapPos, size * zoom), pixmap)
                        #painter.scale(zoom, zoom)                                      # TODO painter.scale() vs. QRect() -> which is faster?
                        #painter.drawPixmap(self.pixmapPos / zoom, pixmap)

                    # at <1 zoom, art.scaled() looks MUCH better and the performance drop is negligible
                    else:
                        if scale == ZOOM_FILL:
                            size = self.size().scaled(pixmap.size(), Qt.KeepAspectRatio) * zoom
                            aspectRatioMode = Qt.IgnoreAspectRatio
                        else:
                            size = pixmap.size() * zoom
                            aspectRatioMode = Qt.KeepAspectRatio
                        painter.drawPixmap(self.pixmapPos, pixmap.scaled(size, aspectRatioMode, transformMode))
                except TypeError:
                    logger.warning(f'(!) QVideoPlayerLabel paintEvent failed due to mismatched pixmapPos type: {format_exc()}')

            # draw normal pixmap. NOTE: for fill-mode, drawing to a QRect NEVER looks identical (it's much worse)
            else:
                #scale = self._artScale if self.isCoverArt else self._imageScale
                if scale == ZOOM_NO_SCALING or (scale == ZOOM_DYNAMIC_FIT and self._baseZoom == 1):
                    self.pixmapPos = self.rect().center() - pixmap.rect().center()
                    painter.drawPixmap(self.pixmapPos, pixmap)
                elif scale == ZOOM_FIT or (scale == ZOOM_DYNAMIC_FIT and self._baseZoom != 1):
                    scaledPixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, transformMode)
                    self.pixmapPos = self.rect().center() - scaledPixmap.rect().center()
                    painter.drawPixmap(self.pixmapPos, scaledPixmap)
                elif scale == ZOOM_FILL:
                    self.pixmapPos = QtCore.QPoint()
                    painter.drawPixmap(0, 0, pixmap.scaled(self.size(), transformMode=transformMode))
        else:
            super().paintEvent(event)

