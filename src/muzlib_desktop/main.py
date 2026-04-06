#!/usr/bin/env python3

import os
import sys
import signal
import base64
import pprint
import urllib.request

# 1. Swapped QGuiApplication for QApplication (required for QFileDialog)
from PySide6.QtWidgets import QApplication, QFileDialog
# 2. Added QObject, Slot, and Signal for the QML bridge
from PySide6.QtCore import QUrl, QObject, Slot, Signal, Property
from PySide6.QtQml import QQmlApplicationEngine
from muzlib.muzlib import Muzlib, SearchType
from PySide6.QtGui import QIcon
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QObject, Signal, Slot, Property, QThread
from muzlib import files_utils

class SearchWorker(QThread):
    searchCompleted = Signal(list)
    searchFailed = Signal(str)

    def __init__(self):
        super().__init__()
        self.ml = None
        self.search_type = None
        self.artist_name = None
        self.album_name = None
        self.song_name = None

    def set_data(self, ml, search_type, artist_name, album_name, song_name):
        self.ml = ml
        self.search_type = search_type
        self.artist_name = artist_name
        self.album_name = album_name
        self.song_name = song_name

    def run(self):
        try:
            results = self.ml.search(
                self.search_type,
                artist_name=self.artist_name,
                album_name=self.album_name,
                song_name=self.song_name
            )
            self.searchCompleted.emit(results)
        except Exception as e:
            self.searchFailed.emit(str(e))

class DownloadWorker(QThread):
    progressChanged = Signal(int, int, str)  # completed, total, track_name
    finished = Signal(str)

    def __init__(self):
        super().__init__()
        self.ml = None
        self.selected_result = None
        self.search_type = None


    def set_data(self, ml, selected_result, search_type):
        self.ml = ml
        self.selected_result = selected_result
        self.search_type = search_type

    def run(self):

        total_songs = self.ml.get_download_summary(self.selected_result, self.search_type)

        complited = 0

        common_path = None
        for track_info in self.ml.get_track_info(self.selected_result, self.search_type):
            song_name = f"{track_info['track_artists_str']} - {track_info['track_name']}"
            self.progressChanged.emit(complited, total_songs, song_name)
            path = self.ml.download_by_track_info(track_info)

            # Calculate the common path of all downloaded songs to open the folder after download
            if common_path is None:
                common_path = path
            else:
                common_path = os.path.commonpath([common_path, path])

            self.progressChanged.emit(complited + 1, total_songs, song_name)

            complited+=1

        common_path = os.path.join(common_path, "") # Add trailing slash to open folder in file manager
        print(common_path)
        self.finished.emit(common_path)




class Backend(QObject):
    # Phase signals
    initializationPhaseChanged = Signal()
    searchingPhaseChanged = Signal()
    downloadingPhaseChanged = Signal()
    finalPhaseChanged = Signal()

    libraryPathChanged = Signal()

    folderSelected = Signal(str)
    previewURLChanged = Signal()
    previewTextChanged = Signal()

    # Search signals
    searchCompleted = Signal()
    searchFailed = Signal(str)
    searchResultCountChanged = Signal()

    # Download signals
    progressChanged = Signal(int, int, str)  # forward worker signal to QML
    downloadFinished = Signal(str)

    def __init__(self):
        super().__init__()
        self.ml = None

        self.defatult_library_path = str(files_utils.get_default_music_directory())
        self.library_path = ""
        self.search_type = ""

        self.search_results = []
        self.search_results_index = 0

        # Setup search worker
        self.search_worker = SearchWorker()
        self.search_worker.searchCompleted.connect(self._on_search_completed)
        self.search_worker.searchFailed.connect(self.searchFailed)

        # Setup download worker
        self.download_worker = DownloadWorker()
        self.download_worker.progressChanged.connect(self.progressChanged)
        self.download_worker.finished.connect(self._on_download_finished)


        self._is_searching = False
        self._preview_url = ""
        self._preview_text = ""

        # Phases
        self._initialization_phase = True
        self._searching_phase = False
        self._downloading_phase = False
        self._final_phase = False
        
    def set_active_phase(self, init=False, searching=False, downloading=False, final=False):
        print(f"Setting phases: init={init}, searching={searching}, downloading={downloading}, final={final}")
        if self._initialization_phase != init:
            self._initialization_phase = init
            self.initializationPhaseChanged.emit()
        
        if self._searching_phase != searching:
            self._searching_phase = searching
            self.searchingPhaseChanged.emit()
            
        if self._downloading_phase != downloading:
            self._downloading_phase = downloading
            self.downloadingPhaseChanged.emit()
            
        if self._final_phase != final:
            self._final_phase = final
            self.finalPhaseChanged.emit()

    def _reset_search_results(self):
        self.search_results = []
        self.search_results_index = 0

        self.previewURL = ""
        self.previewText = ""
    
    @Property(bool, notify=initializationPhaseChanged)
    def initializationPhase(self):
        return self._initialization_phase

    @Property(bool, notify=searchingPhaseChanged)
    def searchingPhase(self):
        return self._searching_phase

    @Property(bool, notify=downloadingPhaseChanged)
    def downloadingPhase(self):
        return self._downloading_phase

    @Property(bool, notify=finalPhaseChanged)
    def finalPhase(self):
        return self._final_phase

    @Property(str,)
    def defaultLibraryPath(self):
        return self.defatult_library_path

    @Property(str, notify=libraryPathChanged)
    def libraryPath(self):
        return self.library_path

    @libraryPath.setter
    def libraryPath(self, value):
        if self.library_path != value:
            self.library_path = value
            self.libraryPathChanged.emit()

    # Define a Property that QML can 'bind' to
    @Property(str, notify=previewURLChanged)
    def previewURL(self):
        return self._preview_url    

    @previewURL.setter
    def previewURL(self, value):
        if self._preview_url != value:
            self._preview_url = value
            self.previewURLChanged.emit() # This triggers the UI update

    @Property(str, notify=previewTextChanged)
    def previewText(self):
        return self._preview_text

    @previewText.setter
    def previewText(self, value):
        if self._preview_text != value:
            self._preview_text = value
            self.previewTextChanged.emit() # This triggers the UI update

    @Property(int, notify=searchResultCountChanged)
    def searchResultCount(self):
        return len(self.search_results)


    @Slot(result=str)
    def open_folder_picker(self):
        directory = QFileDialog.getExistingDirectory(None, "Select Folder", self.library_path)
        if directory:
            # Save the path to our class variable
            self.libraryPath = directory
            return directory
        else:
            print("Selection cancelled.")
            return ""
    

    @Slot(str)
    def open_music_folder(self, path):
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            print(f"Folder not found: {path}")
        
    @Slot(str, str, str, str)
    def search(self, search_type,  artist_name, album_name, song_name):
        self.set_active_phase(searching=True)

        # Reset previous search results
        self._reset_search_results()

        
        if self.library_path == "":
            self.libraryPath = self.defatult_library_path
        
        match search_type.lower():
            case "artist": self.search_type = SearchType.ARTIST
            case "album": self.search_type = SearchType.ALBUM
            case "song": self.search_type = SearchType.SONG

        print(artist_name, album_name, song_name)


        try:
            self.ml = Muzlib(self.library_path)
        except Exception as e:
            self.searchFailed.emit(str(e))
            return

        self.search_worker.set_data(
            self.ml, self.search_type,
            artist_name, album_name, song_name
        )
        self.search_worker.start()

    def _on_search_completed(self, results):
        self.search_results = results
        self.search_results_index = 0
        self.update_search_result()
        self.searchResultCountChanged.emit()
        self.searchCompleted.emit()

    @Slot()
    def download(self):
        if len(self.search_results) == 0:
            print("No search results to download.")
            return
        
        self.set_active_phase(downloading=True)

        selected_result = self.search_results[self.search_results_index]
        self.download_worker.set_data(self.ml, selected_result, self.search_type)
        self.download_worker.start()
    
    def _on_download_finished(self, common_path):
        self.set_active_phase(final=True)
        self.downloadFinished.emit(common_path)

    @Slot()
    def cancel(self):
        self.set_active_phase(init=True)

        self._reset_search_results()
        self.searchResultCountChanged.emit()
        if self.search_worker.isRunning():
            self.search_worker.terminate()
            self._reset_search_results()
            self.searchResultCountChanged.emit()
            print("Search cancelled.")
        if self.download_worker.isRunning():
            self.download_worker.terminate()
            self.progressChanged.emit(0, 0, "Download cancelled.")
            print("Download cancelled.")

        
        
        

    @Slot()
    def next_search_result(self):
        if len(self.search_results) != 0:
            self.search_results_index += 1
            self.search_results_index %= len(self.search_results)
            self.update_search_result()
    
    @Slot()
    def previous_search_result(self):
        if len(self.search_results) != 0:
            self.search_results_index -= 1
            self.search_results_index %= len(self.search_results)
            self.update_search_result()

    @Slot(result=dict)
    def update_search_result(self):
        current_result = self.search_results[self.search_results_index]

        # Change image url
        for thumbnail in current_result["thumbnails"]:
            if thumbnail["width"] <= 200:
                image_url = thumbnail["url"]
            else: break
        
        artist_bold_string = "<b>Artist: </b>"
        artists_bold_string = "<b>Artists: </b>"
        album_bold_string = "<b>Album: </b>"
        title_bold_string = "<b>Title: </b>"
        html_newline = "<br>"
        if self.search_type == self.search_type.ARTIST:
            preview_text = artist_bold_string + current_result["artist"]
        elif self.search_type == self.search_type.ALBUM:
            artist_names = ", ".join([artist["name"] for artist in current_result["artists"]])
            album_name = current_result["title"]

            preview_text = artist_bold_string if len(current_result["artists"]) == 1 else artists_bold_string
            preview_text += artist_names + html_newline + album_bold_string + album_name
        elif self.search_type == self.search_type.SONG:
            artist_names = ", ".join([artist["name"] for artist in current_result["artists"]])
            album_name = current_result["album"]["name"]
            song_name = current_result["title"]

            preview_text = title_bold_string + song_name + html_newline
            preview_text += artist_bold_string if len(current_result["artists"]) == 1 else artists_bold_string
            preview_text += artist_names + html_newline + album_bold_string + album_name

        
        # self.previewURL = image_url
        

        if image_url:
            try:
                # 1. Request the image (Adding a User-Agent helps avoid getting blocked by servers)
                req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    img_bytes = response.read()
                
                # 2. Convert raw bytes to a Base64 string
                b64_str = base64.b64encode(img_bytes).decode('utf-8')
                
                # 3. Format as a Data URI. QML reads this directly from memory!
                self.previewURL = f"data:image/jpeg;base64,{b64_str}"
            except Exception as e:
                print(f"Failed to download image: {e}")
                self.previewURL = "" # Fallback to empty if it fails
        else:
            self.previewURL = ""
        
        self.previewText = preview_text
        

def main():
    """Initializes and manages the application execution"""
    # 3. Use QApplication instead of QGuiApplication

    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    app.setWindowIcon(QIcon("icon.svg"))

    # TODO: add .desktop file and set this properly so that it works in KDE task manager and app switcher
    app.setDesktopFileName("muzlib")

    # 4. Instantiate our backend and expose it to QML as 'backend'
    backend_obj = Backend()
    engine.rootContext().setContextProperty("backend", backend_obj)

    """Needed to close the app with Ctrl+C"""
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # """Needed to get proper KDE style outside of Plasma"""
    # if not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
    #     os.environ["QT_QUICK_CONTROLS_STYLE"] = "org.kde.desktop"

    base_path = os.path.abspath(os.path.dirname(__file__))
    qml_file_path = os.path.join(base_path, "qml", "main.qml")
    url = QUrl.fromLocalFile(qml_file_path)

    engine.load(url)

    if len(engine.rootObjects()) == 0:
        quit()

    app.exec()


if __name__ == "__main__":
    main()
