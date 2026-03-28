"""Text overlay widgets — preview, overlay data, and color picker button."""
from __future__ import annotations

import logging
from traceback import format_exc

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets as QtW

import qthelpers
from pyplayer.widgets.helpers import gui, app, cfg, settings


logger = logging.getLogger('widgets.py')


# ------------------------------------------
# "Add text" Dialog Widgets
# ------------------------------------------
class QTextOverlayPreview(QtW.QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overlays: list[QTextOverlay] = []
        self.selected: QTextOverlay = None                      # TODO ability to select multiple at once
        self.ratio: float = None
        self._draggingOffset: QtCore.QPoint = None
        self._dragging: bool = False


    #def overlayPosToPreviewPos(self, overlay: QTextOverlay) -> QtCore.QPointF:
    #    return overlay.pos * self.ratio


    def getOverlayInRange(self, pos: QtCore.QPoint, _range: int = 30) -> QTextOverlay:
        ''' Returns the index of the closest text overlay to `pos`,
            if any are within `_range` pixels, otherwise None. '''
        min_dist = 1000
        min_overlay = None
        for overlay in self.overlays:
            #font = overlay.font
            #font.setPointSize(overlay.size)

            overlay.font.setPointSize(overlay.size * self.ratio)
            local_pos = overlay.pos * self.ratio
            text_size = QtGui.QFontMetrics(overlay.font).size(0, overlay.text)
            text_rect = QtCore.QRect(local_pos.toPoint(), text_size)

            #text_size = QtGui.QFontMetrics(font).size(0, overlay.text)
            #bottom_right = QtCore.QPoint(local_pos.x() + text_size.width(), local_pos.y() + text_size.height())
            #if QtCore.QRect(local_pos.toPoint(), bottom_right).contains(pos):
            if text_rect.contains(pos):
                min_dist = 0
                min_overlay = overlay

            ##dist = abs(pos.x() - point.x()) + abs(pos.y() - point.y())     # TODO: verify that manhattanLength is actually better than this
            #dist = (pos - (overlay.pos * self.ratio)).manhattanLength()     # https://doc.qt.io/qt-5/qpoint.html#manhattanLength
            #print('DISTANCE', dist)
            #if dist < min_dist:
            #    min_dist = dist
            #    min_overlay = overlay
        return None if min_dist > _range else min_overlay


    def mousePressEvent(self, event: QtGui.QMouseEvent):
        try:
            if event.button() == Qt.LeftButton:
                parent = self.parent()
                overlay = self.getOverlayInRange(event.pos())
                print('OVERLAY IN RANGE?', overlay)

                if not self.selected.text.strip():
                    try: self.overlays.pop(self.overlays.index(self.selected))
                    except: pass

                if not overlay:
                    #overlay = QTextOverlay(parent.comboFont.currentFont(), parent.spinFontSize.value())
                    overlay = QTextOverlay(parent)
                    overlay.pos = QtCore.QPointF(event.pos()) / self.ratio
                    self.overlays.append(overlay)
                    parent.text.setFocus(True)

                if overlay is not self.selected:
                    self.selected = overlay
                    parent.text.setPlainText(overlay.text)
                    parent.comboFont.setCurrentFont(overlay.font)
                    parent.spinFontSize.setValue(overlay.size)
                    parent.spinBoxWidth.setValue(overlay.bgwidth)
                    parent.buttonColorFont.setStyleSheet('QPushButton {background-color: rgba' + str(overlay.color.getRgb()) + ';border: 1px solid black;}')
                    parent.buttonColorBox.setStyleSheet('QPushButton {background-color: rgba' + str(overlay.bgcolor.getRgb()) + ';border: 1px solid black;}')
                    parent.buttonColorShadow.setStyleSheet('QPushButton {background-color: rgba' + str(overlay.shadowcolor.getRgb()) + ';border: 1px solid black;}')
                    {
                        Qt.AlignLeft:    parent.buttonAlignLeft,
                        Qt.AlignHCenter: parent.buttonAlignCenter,
                        Qt.AlignRight:   parent.buttonAlignRight
                    }[overlay.alignment].setChecked(True)

                self._draggingOffset = event.pos() - (overlay.pos * self.ratio)
                self._dragging = True
                self.update()

        except:
            print('mousepress', format_exc())


    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        try:
            if event.buttons() == Qt.LeftButton and self._dragging:
                centered = False
                overlay = self.selected
                local_pos = event.pos() - self._draggingOffset

                # hold ctrl for free dragging
                if event.modifiers() & Qt.ControlModifier:
                    overlay.centered_horizontally = False
                    overlay.centered_vertically = False
                    overlay.pos = local_pos / self.ratio

                # otherwise, the text is snapped to an axis if close enough
                else:
                    #text_size = QtGui.QFontMetrics(overlay.font).size(0, overlay.text.strip('\n'))
                    text_size = QtGui.QFontMetrics(overlay.font).size(0, overlay.text)
                    text_pos_rect = QtCore.QRect(local_pos.toPoint(), text_size)
                    text_center = text_pos_rect.center()
                    horizontal_center = self.width() / 2
                    vertical_center = self.height() / 2

                    # check if we should snap to the horizontal center (locked x)
                    if abs(text_center.x() - horizontal_center) < 20:
                        text_pos_rect.moveCenter(QtCore.QPoint(horizontal_center, text_center.y()))
                        overlay.centered_horizontally = True
                        centered = True
                    else:
                        overlay.centered_horizontally = False

                    # check if we should snap to the vertical center (locked y)
                    if abs(text_center.y() - vertical_center) < 20:
                        text_pos_rect.moveCenter(QtCore.QPoint(text_pos_rect.center().x(), vertical_center))
                        overlay.centered_vertically = True
                        centered = True
                    else:
                        overlay.centered_vertically = False

                    # update text overlay position depending on if we snapped to a center or not
                    if centered:
                        overlay.pos = QtCore.QPointF(text_pos_rect.x(), text_pos_rect.y()) / self.ratio
                    else:
                        overlay.pos = local_pos / self.ratio
                self.update()                                   # manually update
        except: print('mousemove', format_exc())


    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        local_pos = self.selected.pos * self.ratio
        text_size = QtGui.QFontMetrics(self.selected.font).size(0, self.selected.text)
        text_pos_rect = QtCore.QRect(local_pos.toPoint(), text_size)
        if not self.rect().contains(text_pos_rect.center()):
            logging.info('Text overlay dragged out of the preview, deleting...')
            try: self.overlays.pop(self.overlays.index(self.selected))
            except: pass

        self._dragging = False
        self.update()                                           # manually update


    def paintEvent(self, event: QtGui.QPaintEvent):
        super().paintEvent(event)                               # perform built-in paint immediately so we can paint on top

        p = QtGui.QPainter()
        p.begin(self)
        try:
            for overlay in self.overlays:
                text = overlay.text.strip('\n')

                #size = settings.spinHoverFontSize.value()   # TODO use currentFontChanged signals + more for performance? not needed?
                #font = settings.comboHoverFont.currentFont()

                #font = overlay.family
                #font.setPointSize(overlay.size)
                #p.setFont(font)
                #color = overlay.color
                #color.setAlpha(overlay.alpha)
                #p.setPen(color)
                #overlay.font.setPointSize(overlay.size * self.ratio)
                #overlay.font.setPointSize(overlay.size * self.ratio)

                #if overlay.size % 2 == 0:
                #    overlay.font.setPointSize(overlay.size * self.ratio)
                #else:
                #    overlay.font.setPixelSize(overlay.size * self.ratio)

                # FFmpeg uses pixel size
                overlay.font.setPixelSize(overlay.size * self.ratio)

                #overlay.color.setAlpha(overlay.alpha)
                p.setFont(overlay.font)
                p.setPen(overlay.color)
                #p.setLine
                fm = p.fontMetrics()

                #color = QtGui.QColor(overlay.color)
                #color.setAlpha(overlay.alpha)
                #p.setPen(color)

                local_pos = overlay.pos * self.ratio
                text_size = fm.size(0, text)
                #text_pos_rect = QtCore.QRect(local_pos.toPoint(), text_size)
                text_pos_rect = QtCore.QRectF(local_pos, QtCore.QSizeF(text_size))
                print('DRAWING AT!!', local_pos, text_pos_rect.center().x(), self.width() / 2)

                ##local_pos.setY(self.height() - (self.height() - overlay.size) / 2)
                ##p.drawText(local_pos, text)
                ##text_width = QtGui.QFontMetrics(font).width(text)
                ##text_size = QtGui.QFontMetrics(font).size(0, text)
                #text_size = fm.size(0, text)
                ##bottom_right = QtCore.QPointF(local_pos.x() + text_size.width(), local_pos.y() + text_size.height())
                ##p.drawText(QtCore.QRect(local_pos, bottom_right), 0, text)
                ##bottom_right = QtCore.QPoint(local_pos.x() + text_size.width(), local_pos.y() + text_size.height())
                ##text_rect = QtCore.QRect(local_pos.toPoint(), bottom_right)
                #text_rect = QtCore.QRect(local_pos.toPoint(), text_size)

                #text_rect = fm.boundingRect(text)

                #text_boundary_rect = fm.tightBoundingRect(text)
                ##text_rect.setHeight(QtGui.QFontMetrics(overlay.font).ascent())
                #print('tight:', text_boundary_rect)

                #text_boundary_rect.translate(local_pos.toPoint())
                #text_pos_rect.adjust(text_boundary_rect.x(), text_boundary_rect.y(), 0, 0)
                #text_pos_rect.translate(-text_boundary_rect.x() // 2, text_boundary_rect.y() // 2)
                #text_boundary_rect.moveTo(local_pos.toPoint())

                ##x = QtCore.QPoint(local_pos.x() + text_boundary_rect.x(), local_pos.y() - text_boundary_rect.y())
                #x = QtCore.QPoint(local_pos.x() + text_boundary_rect.x(), local_pos.y() + fm.descent() + 1)
                #text_boundary_rect.moveTo(x)
                ##text_boundary_rect.translate(text_boundary_rect.x(), text_boundary_rect.y())

                # draw background first (or a simple outline and snap-lines if we're dragging)
                #if self._dragging and overlay is self.selected: p.drawRect(text_boundary_rect)
                #else: p.fillRect(text_boundary_rect, overlay.bgcolor)
                if self._dragging and overlay is self.selected:
                    p.drawRect(text_pos_rect)
                    if overlay.centered_horizontally:
                        p.drawLine(self.width() / 2, 0, self.width() / 2, self.height())
                    if overlay.centered_vertically:
                        p.drawLine(0, self.height() / 2, self.width(), self.height() / 2)
                else:
                    p.fillRect(text_pos_rect, overlay.bgcolor)

                # draw text over background (drop-shadow first)
                if overlay.shadowx or overlay.shadowy:
                    p.setPen(overlay.shadowcolor)
                    p.drawText(text_pos_rect.translated(overlay.shadowx, overlay.shadowy), overlay.alignment | Qt.AlignTop, text)
                    p.setPen(overlay.color)
                p.drawText(text_pos_rect, overlay.alignment | Qt.AlignTop, text)

                #richtext = text.replace('\n', '<br>')
                #richertext = f'<p style="line-height:0.8">{richtext}</p>'
                #p.drawStaticText(local_pos, QtGui.QStaticText(richertext))
                #td = QtGui.QTextDocument()
                #td.setHtml(text)
                #td.drawContents(p, text_pos_rect)
        except:
            print('TEXTADDPAINT', format_exc())
        finally:
            p.end()




class QTextOverlay:
    def __init__(self, dialog):
        self.text = ''
        self.pos = QtCore.QPointF(0.0, 0.0)
        self.font: QtGui.QFont = dialog.comboFont.currentFont()
        self.size: int = dialog.spinFontSize.value()
        self.color = self.get_color_from_stylesheet(dialog.buttonColorFont.styleSheet())
        self.bgcolor = self.get_color_from_stylesheet(dialog.buttonColorBox.styleSheet())
        self.bgwidth: int = dialog.spinBoxWidth.value()
        self.shadowcolor = self.get_color_from_stylesheet(dialog.buttonColorShadow.styleSheet())
        self.shadowx = dialog.spinShadowX.value()
        self.shadowy = dialog.spinShadowY.value()
        self.alignment: Qt.Alignment = {
            dialog.buttonAlignLeft:   Qt.AlignLeft,
            dialog.buttonAlignCenter: Qt.AlignHCenter,
            dialog.buttonAlignRight:  Qt.AlignRight
        }[dialog.buttonGroup.checkedButton()]
        self.centered_horizontally = False
        self.centered_vertically = False


    def get_color_from_stylesheet(self, stylesheet: str) -> QtGui.QColor:
        ''' Returns the first "rgba()" in a `stylesheet` as a `QColor`. '''
        start_index = stylesheet.find('rgba(') + 5
        end_index = stylesheet.find(');', start_index)
        rgba = stylesheet[start_index:end_index].replace(' ', '').split(',')
        return QtGui.QColor(*(int(v) for v in rgba))



# ------------------------------------------
# Utility Widgets
# ------------------------------------------
class QColorPickerButton(QtW.QPushButton):
    ''' A button representing a color that may be clicked to display and handle
        a color picker. Clicking and dragging the button will turn the mouse into
        an eyedropper tool, allowing users to select a color from their screen.
        Adjusts its stylesheet and tooltip to display the color it represents.
        Custom stylesheets & tooltips may be used as a base and are accessible/
        editable as properties.

        Emits a custom `colorChanged` signal upon successfully changing
        the color. Uses white text for dark colors. Scrolling over the button
        will adjust its color's alpha value, if the alpha channel is enabled.
        Middle-clicking the button will toggle the alpha (if enabled) between
        0 and the most recent non-0 value.

        NOTE: `parseStyleSheet()` must be manually called to initialize the
        button's color. The button's base stylesheet must include the button's
        `background-color` attribute (and it must be the first attribute of the
        first styled widget) before `parseStyleSheet()` may be called.

        NOTE: This class is designed around using `QColor.getRgb()` instead of
        `QColor.name()`, with stylesheets using "rgb(r,g,b)/rbga(r,g,b,a)"
        formatting instead of #RRGGBB/#AARRGGBB. '''

    colorChanged = QtCore.pyqtSignal(QtGui.QColor)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clicked.connect(self.showColorPicker)
        self.color: QtGui.QColor = None
        self.alphaEnabled = True
        self.storedAlpha = 150
        self.toolTipBase = ''
        self.styleSheetSuffix = ''
        self._timer: int = None
        self._dragging = False
        self._predragColor: QtGui.QColor = None
        self._parentCursor: Qt.CursorShape = None


    def setAlphaEnabled(self, enabled: bool):
        self.alphaEnabled = enabled


    def setStoredAlpha(self, alpha: int):
        self.storedAlpha = alpha


    def setToolTipBase(self, tooltip: str):
        self.toolTipBase = tooltip


    def parseStyleSheet(self):
        ''' Initialize this button's color by parsing its stylesheet. This may
            be called as many times as desired, but realisitically only needs
            to be done once. '''
        stylesheet = self.styleSheet()

        # Example: 'QPushButton { background-color: rgba(255,255,255,255); }'
        start = stylesheet.find('background-color: rgb') + 22
        if start == 21:
            return
        if stylesheet[start - 1] == 'a':
            start += 1
        end = stylesheet.find(')', start)
        self.styleSheetSuffix = stylesheet[end + 1:]            # strip ')' from start of suffix
        color = self.setColorString(stylesheet[start:end])
        self.storedAlpha = color.alpha() or self.storedAlpha


    def setColor(self, color: QtGui.QColor, enableAlpha: bool = None) -> str:
        ''' Sets `self.color` to `color`, updates the tooltip/stylesheet, emits
            a `self.colorChanged` signal, and returns the new string `color`
            represents. `self.alphaEnabled` will be updated if `enableAlpha`
            is provided. '''
        self.color = color

        # shortcut for toggling alpha channel
        if enableAlpha is not None:
            self.alphaEnabled = enableAlpha

        # if alpha is enabled, change stylesheet/tooltip accordingly
        if self.alphaEnabled:
            prefix = 'QPushButton{background-color:rgba'
            tooltip_suffix = '\nClick/drag for color picker.\nMiddle-click to toggle alpha.\nScroll to increment alpha.'
        else:
            prefix = 'QPushButton{background-color:rgb'
            tooltip_suffix = ''

        # get color string and update tooltip/stylesheet
        color_string = str(color.getRgb())
        self.setToolTip(f'{self.toolTipBase} {color_string}{tooltip_suffix}')

        # -> use white text if button is too dark - https://en.wikipedia.org/wiki/HSL_and_HSV
        if color.value() < 50 and color.alpha() > 100:
            self.setStyleSheet(f'{prefix}{color_string};color:white{self.styleSheetSuffix}')
        else:
            self.setStyleSheet(f'{prefix}{color_string}{self.styleSheetSuffix}')

        # emit signal and return the string version of the provided `color`
        self.colorChanged.emit(color)
        return color_string


    def setColorString(self, string: str) -> QtGui.QColor:
        ''' Converts `string` to a `QColor` if possible, assigns it
            to `self.color`, updates the tooltip/stylesheet, emits
            a `self.colorChanged` signal, and returns the new color.

            `string` should loosely follow the format of "r,g,b,a".
            `self.alphaEnabled` will be updated to match whether
            or not `color_string` included an alpha value. '''

        # strip opening/closing parenthesis and remove all spaces
        color_string = string.strip('()').replace(' ', '')
        color_parts = color_string.split(',')
        color = self.color = QtGui.QColor(*(int(v) for v in color_parts))

        if len(color_parts) == 4:
            self.alphaEnabled = True
            prefix = 'QPushButton{background-color:rgba'
            tooltip_suffix = '\nClick/drag for color picker.\nMiddle-click to toggle alpha.\nScroll to increment alpha.'
        else:
            self.alphaEnabled = False
            prefix = 'QPushButton{background-color:rgb'
            tooltip_suffix = ''

        self.setToolTip(f'{self.toolTipBase} ({color_string.replace(",", ", ")}){tooltip_suffix}')
        if color.value() < 50 and color.alpha() > 100:          # use white text if button is too dark
            self.setStyleSheet(f'{prefix}({color_string});color:white{self.styleSheetSuffix}')
        else:
            self.setStyleSheet(f'{prefix}({color_string}){self.styleSheetSuffix}')

        self.colorChanged.emit(color)
        return color


    def showColorPicker(self, initialColor: QtGui.QColor = None, alpha: bool = None) -> QtGui.QColor | None:
        ''' Shows Qt's native color picking dialog set to `self.color`
            by default and showing the alpha channel if `self.alphaEnabled`
            is True, with `initialColor` and `alpha` acting as overrides if
            provided (`alpha` will also update `self.alphaEnabled` on success).
            If a valid color is chosen, `self.setColor()` is called and the new
            color is returned. Otherwise, the starting color is returned. '''
        initialColor = initialColor or self.color
        alpha = self.alphaEnabled if alpha is None else alpha

        # NOTE: F suffix is Float -> values are represented from 0-1 (e.g. getRgb() becomes getRgbF())
        try:
            picker = QtW.QColorDialog()
            #for index, default in enumerate(self.defaults):
            #    picker.setCustomColor(index, QtGui.QColor(*default))

            # open color picker with appropriate arguments
            kwargs = dict(initial=initialColor, parent=self.parent(), title='Picker? I hardly know her!')
            if alpha: color = picker.getColor(**kwargs, options=QtW.QColorDialog.ShowAlphaChannel)
            else:     color = picker.getColor(**kwargs)

            # return the starting color if selected color is invalid
            if not color.isValid():
                return initialColor

            # update/return our selected color and update `self.alphaEnabled`
            self.alphaEnabled = alpha
            self.setColor(color)
            return color
        except:
            logger.warning(f'(!) OPEN_COLOR_PICKER FAILED: {format_exc()}')
            return initialColor


    def wheelEvent(self, event: QtGui.QWheelEvent):
        ''' Increments `self.color`'s alpha value if possible:
            5 by default, 15 if `Ctrl` is held, 1 if `Alt` is held. '''
        if not self.alphaEnabled:
            return

        mod = event.modifiers()
        if mod & Qt.AltModifier:
            self.color.setAlpha(self.color.alpha() + (1 if event.angleDelta().x() > 0 else -1))
        else:
            delta = 15 if mod & Qt.ControlModifier else 5
            self.color.setAlpha(self.color.alpha() + (delta if event.angleDelta().y() > 0 else -delta))
        self.setColor(self.color)


    def mousePressEvent(self, event: QtGui.QMouseEvent):
        ''' Toggles the current color's alpha between 0 and
            the most recent non-zero alpha on middle-click. '''
        if event.button() == Qt.MiddleButton and self.alphaEnabled:
            color = self.color
            alpha = color.alpha()
            if alpha:                       # only store/update alpha if it's non-zero
                self.storedAlpha = alpha
                color.setAlpha(0)
            else:
                color.setAlpha(self.storedAlpha)
            self.setColor(color)
        else:
            super().mousePressEvent(event)


    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        ''' Updates our color to whatever pixel on the screen the mouse is
            currently hovering over, if we're left-click dragging. If we're
            dragging but left-click isn't the sole button being held, the
            eyedropper is cancelled. Overrides the cursor to a precision
            cursor while color picking if we're not hovering over
            ourselves, otherwise a warning cursor is used. '''
        # there are many ways this can be done (like with timers), but just spamming it is honestly fine
        # NOTE: override-cursors must be used as a widget's normal cursor is not honored while dragging
        if event.buttons() == Qt.LeftButton:
            if self._dragging:
                if self.rect().contains(event.pos()):       # NOTE: self.underMouse() does not work...
                    if self.color != self._predragColor:    # ...here, even with `setMouseTracking(True)`
                        self.setColor(self._predragColor)
                    qthelpers.setCursor(Qt.ForbiddenCursor, conditionally=True)
                else:
                    new_color = qthelpers.getPixelColor(alpha=self.color.alpha())
                    if self.color != new_color:
                        self.setColor(new_color)
                    qthelpers.setCursor(Qt.CrossCursor, conditionally=True)
                return

            self._predragColor = self.color
            self._dragging = True

        # cancel if anything other than solely left-click is held while moving
        elif self._dragging:                                # NOTE: these clicks cannot be detected...
            self.setColor(self._predragColor)               # ...in `mousePressEvent`() while dragging
            qthelpers.resetCursor()
            self._dragging = False


    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        ''' Finalizes and disables the eyedropper (and its cursor) if it
            was active, cancelling it if we released over ourselves. '''
        if self._dragging and event.button() == Qt.LeftButton:
            # reset color if we released over the button (NOTE: self.underMouse() does not work here)
            # otherwise, get pixel again to ensure we have the true final color under our mouse
            if self.rect().contains(self.mapFromGlobal(QtGui.QCursor.pos())):
                self.setColor(self._predragColor)
            else:
                self.setColor(qthelpers.getPixelColor(alpha=self.color.alpha()))

            self._dragging = False
            qthelpers.resetCursor()
        else:
            return super().mouseReleaseEvent(event)


    def keyPressEvent(self, event: QtGui.QKeyEvent):
        ''' Cancels the eyedropper if Esc is pressed. '''
        if self._dragging and event.key() == Qt.Key_Escape:
            self.setColor(self._predragColor)
            qthelpers.resetCursor()
            self._dragging = False
        else:
            return super().keyPressEvent(event)


