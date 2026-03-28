"""QVideoList and QVideoListItemWidget — concatenation dialog list widgets."""
from __future__ import annotations

import logging
from traceback import format_exc

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets as QtW

from pyplayer.widgets.helpers import gui, app, cfg, settings


logger = logging.getLogger('widgets.py')


# ------------------------------------------
# Concatenation Widgets
# ------------------------------------------
class QVideoListItemWidget(QtW.QWidget):                        # TODO this likely does not get garbage collected
    ''' An item representing a media file within a
        `QVideoList`, within the concatenation menu. '''
    def __init__(
        self,
        parent: QtW.QWidget,
        thumbnail_path: str,
        text: str,
        is_playing: bool
    ):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.layout = QtW.QHBoxLayout()                         # ^ required for dragging to work
        self.setLayout(self.layout)

        self.thumbnail = QtW.QLabel(self)
        self.thumbnail.setPixmap(QtGui.QPixmap(thumbnail_path))
        self.thumbnail.setAlignment(Qt.AlignCenter)

        # put outline around thumbnail if this item is currently playing
        if not is_playing:
            self.thumbnail.setStyleSheet('QLabel { padding: 4px; }')
        else:
            self.thumbnail.setStyleSheet(
                'QLabel { padding: 4px; background-color: '
                'qlineargradient(spread:pad,x1:0,y1:0,x2:0,y2:1,'
                'stop:0.573864 rgba(0,255,255,255),stop:1 rgba(0,0,119,255)); }'
            )

        self.label = QtW.QLabel(text, self)
        #self.label.setStyleSheet('QLabel { padding-left: 1px; }')
        #self.layout.addSpacerItem(QtW.QSpacerItem(2, 20, QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Minimum))

        self.layout.addWidget(self.thumbnail)
        self.layout.addWidget(self.label)
        self.layout.addSpacerItem(QtW.QSpacerItem(40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum))
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(1, 0, 0, 0)




class QVideoList(QtW.QListWidget):                              # TODO this likely is not doing any garbage collection
    ''' A list of interactable media files represented by
        `QVideoListItemWidget`'s within the concatenation menu. '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)


    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):     # drag and drop requires self.setAcceptDrops(True)
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()
        super().dragEnterEvent(event)                           # run QWidget's built-in behavior


    def dropEvent(self, event: QtGui.QDropEvent):
        ''' Handles adding externally dropped items to the list, and includes
            an ugly workaround for a Qt bug that creates duplicated and/or
            invisible items when dragging an item below itself without
            actually changing its final position. '''
        old_items = tuple(qthelpers.listGetAllItems(self))
        files = tuple(url.toLocalFile() for url in event.mimeData().urls())
        if files:
            self.add(files=files)

        # reset and force arrow cursor so it doesn't get erroneously hidden
        qthelpers.setCursor(Qt.ArrowCursor)

        # run QWidget's built-in behavior
        super().dropEvent(event)

        # if no files were dropped, assume we did an internal drag/drop -> fix Qt bug
        if not files:
            event.ignore()                                      # ignoring the event prevents original item from getting deleted
            for item in qthelpers.listGetAllItems(self):        # cycle through items and
                if item not in old_items:                       # look for "new" item that appeared
                    garbage = self.takeItem(self.row(item))     # delete corrupted item
                    del garbage


    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Creates a context menu for the `QListWidgetItem` underneath
            the mouse, if any. This could alternatively be accomplished
            through the `itemClicked` signal. '''
        item = self.itemAt(event.pos())                         # get item under mouse to work with
        if not item: return                                     # no item under mouse, return
        path = item.toolTip()

        def play_and_refresh():
            gui.open(
                path,
                focus_window=False,
                flash_window=False,
                update_recent_list=path in gui.recent_files,
                update_raw_last_file=False
            )
            self.refresh_thumbnail_outlines()

        def set_output_part(*, filename: bool = True):
            output = self.parent().output
            old_path = output.text().strip()
            if filename:                                        # replace filename
                dirname = os.path.dirname(old_path)
                if dirname:
                    dirname += '/'
                output.setText(os.path.normpath(dirname + os.path.basename(path)))
            else:                                               # replace dirname
                filename = os.path.basename(old_path)
                new_path = os.path.normpath(f'{os.path.dirname(path)}/{filename}')
                if not filename:
                    new_path += os.sep
                output.setText(new_path)

        action1 = QtW.QAction('&Play')
        action1.triggered.connect(play_and_refresh)
        action2 = QtW.QAction('&Explore')
        action2.triggered.connect(lambda: qthelpers.openPath(path, explore=True))
        action3 = QtW.QAction('&Remove')
        action3.triggered.connect(lambda: qthelpers.listRemoveSelected(self))
        action4 = QtW.QAction('&Set as output filename')
        action4.triggered.connect(set_output_part)
        action5 = QtW.QAction('&Set as output folder')
        action5.triggered.connect(lambda: set_output_part(filename=False))
        action6 = QtW.QAction('&Set as output path')
        action6.triggered.connect(lambda: self.parent().output.setText(path))

        context = QtW.QMenu(self)
        context.addActions((action1, action2, action3))
        context.addSeparator()
        context.addActions((action4, action5, action6))
        context.exec(event.globalPos())


    def add(self, *, files: str | tuple[str] = None, index: int = None):
        ''' Adds a list/tuple of `files` as `QVideoListItemWidget`'s. If `files`
            is a string, it will be interpreted as the sole element of a tuple.
            If `index` is specified, `files` will be inserted at that spot. '''
        if isinstance(files, str):
            files = (files,)
        elif files is None:
            files, cfg.lastdir = qthelpers.browseForFiles(
                lastdir=cfg.lastdir,
                caption='Select video to add',
                filter='MP4 files (*.mp4);;All files (*)'
            )

        # create QVideoListItemWidgets on top of QListWidgetItems for each file
        thumbnails_needed = []
        for file in files:
            if not file or not os.path.exists(file):
                continue

            file = os.path.abspath(file)
            basename = os.path.basename(file)
            thumbnail_name = get_unique_path(basename.replace('/', '.').replace('\\', '.'))
            thumbnail_path = os.path.join(constants.THUMBNAIL_DIR, f'{thumbnail_name}_thumbnail.jpg')
            last_modified = time.strftime('%#m/%#d/%y | %#I:%M:%S%p', time.localtime(os.path.getmtime(file))).lower()
            html = f'<html><head/><body><p style="line-height:0.5"><span style="font-family:Yu Gothic; font-size:12pt;">{basename}</span></p><p><span style="color:#676767;">{last_modified}</span></p></body></html>'
            item_widget = QVideoListItemWidget(
                parent=self,
                thumbnail_path=thumbnail_path,
                text=html,
                is_playing=file == gui.video
            )

            # create and setup QListWidgetItem as the base for our QVideoListItemWidget with our file and QLabel
            if index is None:
                item_base = QtW.QListWidgetItem(self)
            else:
                item_base = QtW.QListWidgetItem()
                self.insertItem(index, item_base)
            item_base.setToolTip(file)
            self.setItemWidget(item_base, item_widget)
            item_base.setSizeHint(QtCore.QSize(0, 64))          # default width/height is -1, but this is invalid. yeah.

            # check if thumbnail actually existed or not
            if not os.path.exists(thumbnail_path):              # check if thumbnail existed or not
                thumbnails_needed.append((file, thumbnail_path, item_widget))

        # ensure thumbnail folder exists, then create threads to generate thumbnails
        if not os.path.exists(constants.THUMBNAIL_DIR):
            os.makedirs(constants.THUMBNAIL_DIR)
        if thumbnails_needed:
            Thread(target=self.generate_thumbnails, args=thumbnails_needed, daemon=True).start()

        # refresh titlebar to show number of QVideoListItemWidgets
        self.refresh_title()


    def remove(self):
        ''' Removes all selected `QVideoListItemWidget`'s and updates title. '''
        qthelpers.listRemoveSelected(self)
        self.refresh_title()


    def generate_thumbnails(self, *thumbnail_args: tuple[str, str, QVideoListItemWidget], _delete: list = None):
        ''' Generates/saves thumbnails for an indeterminate number of tuples
            consisting of the vide to generate the thumbnail from, a path to
            save the thumbnail to, and the `QVideoListItemWidget` to apply the
            thumbnail to. Thumbnails are generated concurrently, but only 16
            at a time. `constants.FFMPEG` is assumed to be valid. '''

        logger.info(f'Getting thumbnails for {len(thumbnail_args)} file(s)')
        _thumbnail_args = thumbnail_args[:16]                    # only do 16 at a time
        excess = thumbnail_args[16:]
        stage1 = []
        stage2 = []
        to_delete = _delete or []

        # begin ffmpeg process for each file and immediately jump to the next file
        # generate thumbnail from 3 seconds into each file
        for file, thumbnail_path, item_widget in _thumbnail_args:
            temp_path = thumbnail_path.replace('_thumbnail', '_thumbnail_unscaled')
            stage1.append(
                (
                    temp_path,
                    thumbnail_path,
                    item_widget,
                    ffmpeg_async(f'-ss 3 -i "{file}" -vframes 1 "{temp_path}"')
                )                                                # ^ "-ss 3" gets a frame from 3 seconds in
            )

        # wait for each process and then repeat
        # this time we're resizing the thumbnails we just generated
        for temp_path, thumbnail_path, item_widget, process in stage1:
            process.communicate()
            if not os.path.exists(temp_path):                    # thumbnail won't generate if video is <3s long
                ffmpeg(f'-i "{file}" -vframes 1 "{temp_path}"')  # try again, getting the first frame instead
            stage2.append(
                (
                    temp_path,
                    thumbnail_path,
                    item_widget,
                    ffmpeg_async(f'-i "{temp_path}" -vf scale=-1:56 "{thumbnail_path}"')
                )
            )

        # wait once again and apply the thumbnail to its associated widget
        for temp_path, thumbnail_path, item_widget, process in stage2:
            process.communicate()
            item_widget.thumbnail.setPixmap(QtGui.QPixmap(thumbnail_path))
            to_delete.append(temp_path)

        # recursively generate 16 thumbnails at a time until finished
        if excess:
            return self.generate_thumbnails(*excess, _delete=to_delete)

        # delete all temporary files. keep trying for 1.5 seconds if necessary
        attempts = 3
        while to_delete and attempts > 0:
            for index in range(len(to_delete) - 1, -1, -1):
                try: os.remove(to_delete[index])
                except FileNotFoundError: pass
                except: continue
                to_delete.pop(index)
            attempts -= 1
            time.sleep(0.5)


    def refresh_thumbnail_outlines(self):
        for item in self:
            set_style = self.itemWidget(item).thumbnail.setStyleSheet
            if item.toolTip() != gui.video: set_style('QLabel { padding: 4px; }')
            else: set_style('QLabel { padding: 4px;background-color: qlineargradient(spread:pad,x1:0,y1:0,x2:0,y2:1,stop:0.573864 rgba(0,255,255,255),stop:1 rgba(0,0,119,255)); }')


    def refresh_title(self):
        ''' Refreshes parent's titlebar to mention the current file count. '''
        count = self.count()
        if count < 2: self.parent().setWindowTitle('Videos to concatenate')
        else:         self.parent().setWindowTitle(f'{count} videos to concatenate')


    def move(self, *, down: bool = False):
        ''' Moves all selected items up or `down`, while maintaining selection.
            Achieved by duplicating selected items and inserting them one index
            away, before deleting the original items. '''
        indexes = sorted(self.row(item) for item in self.selectedItems())
        for old_index in (reversed(indexes) if down else indexes):
            new_index = old_index + (1 if down else -1)
            new_index = min(self.count() - 1, max(0, new_index))
            if old_index != new_index:
                self.add(files=self.takeItem(old_index).toolTip(), index=new_index)
                self.item(new_index).setSelected(True)          # ^ same corrupted item bug affects moving items


    def reverse(self):
        ''' Reverses items in list by cloning list backwards, then
            deleting the original items. Preserves selection. '''
        count = self.count()
        selected_indexes = sorted(count - self.row(item) - 1 for item in self.selectedItems())
        for index in reversed(range(count)):
            self.add(files=self.item(index).toolTip())
            self.takeItem(index)
        for index in selected_indexes:
            self.item(index).setSelected(True)
        self.refresh_title()


    def __iter__(self):
        for i in range(self.count()):
            yield self.item(i)


