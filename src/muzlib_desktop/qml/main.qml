import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
// import Qt.labs.platform 1.1 // Required for FolderDialog
// import org.kde.kirigami as Kirigami
// import org.kde.simplemdviewer 1.0


ApplicationWindow {
    id: root

    title: "Muzlib"
    visible: true

    // minimumWidth: Kirigami.Units.gridUnit * 30
    // minimumHeight: Kirigami.Units.gridUnit * 30
    // width: minimumWidth
    // height: minimumHeight

    minimumWidth: 480
    minimumHeight: 600 //480
    width: minimumWidth
    height: minimumHeight

    // pageStack.initialPage: initPage
    StackView {
        id: pageStack
        anchors.fill: parent
        initialItem: initPage
    }

    Component {
        id: initPage

        Page  {
            // padding: Kirigami.Units.gridUnit
            padding: 16

            ScrollView {
                anchors.fill: parent
                contentWidth: availableWidth
                clip: true // Keeps scrolling content from spilling outside the view

                ColumnLayout {
                    width: parent.width

                    Label {
                        text: "1. Select library directory"
                        font.bold: true
                    }
                    RowLayout {
                        Layout.fillWidth: true

                        Button {
                            text: "Select Folder"
                            visible: backend.initializationPhase

                            onClicked:{
                                let path = backend.open_folder_picker()
                                libraryPath.text = path
                            }
                        }
                        Label {
                            text: "Selected Folder:"
                            visible: !backend.initializationPhase
                        }
                        NavigableTextArea {
                            id: libraryPath
                            // text: backend.libraryPath
                            Layout.fillWidth: true
                            readOnly: !backend.initializationPhase
                            placeholderText: backend.defaultLibraryPath //libraryPath
                            text: backend.libraryPath

                            // Layout.minimumHeight: Kirigami.Units.gridUnit
                            Layout.minimumHeight: 16
                        }
                    }
                    
                    Label {
                        text: "2.Select download type:"
                        font.bold: true
                    }
                    ButtonGroup {
                        id: searchTypeGroup
                    }
                    RowLayout {
                        // anchors.centerIn: parent
                        spacing: 10

                        RadioButton {
                            id: discographyRadioButton

                            property string backendText: "artist"

                            ButtonGroup.group: searchTypeGroup

                            text: "Artist"
                            checked: true
                            checkable: backend.initializationPhase
                            font.bold: checked
                        }

                        RadioButton {
                            id: albumRadioButton
                            
                            property string backendText: "album"

                            ButtonGroup.group: searchTypeGroup

                            text: "Album"
                            checked: false
                            checkable: backend.initializationPhase
                            font.bold: checked
                        }

                        RadioButton {
                            id: singleRadioButton

                            property string backendText: "song"

                            ButtonGroup.group: searchTypeGroup

                            text: "Song"
                            checked: false
                            checkable: backend.initializationPhase
                            font.bold: checked
                        }
                    }
                    Label {
                        text: "3. Write information about the artist/album/song:"
                        font.bold: true
                    }
                    NavigableTextArea {
                        id: artistInput

                        // Layout.minimumHeight: Kirigami.Units.gridUnit
                        Layout.minimumHeight: 16

                        placeholderText: "Artist name"
                        readOnly: !backend.initializationPhase
                        
                    }
                    NavigableTextArea {
                        id: albumInput

                        // Layout.minimumHeight: Kirigami.Units.gridUnit
                        Layout.minimumHeight: 16

                        placeholderText: "Album name"
                        visible: albumRadioButton.checked
                        readOnly: !backend.initializationPhase
                        
                    }
                    NavigableTextArea {
                        id: songInput

                        // Layout.minimumHeight: Kirigami.Units.gridUnit
                        Layout.minimumHeight: 16

                        placeholderText: "Song name"
                        visible: singleRadioButton.checked
                        readOnly: !backend.initializationPhase
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        Button {
                            text: "Search"
                            enabled: backend.initializationPhase || backend.finalPhase
                            onClicked: {
                                searchingIndicator.running = true
                                searchResultContainer.visible = false

                                backend.search(
                                    searchTypeGroup.checkedButton.backendText,
                                    artistInput.text,
                                    albumInput.text,
                                    songInput.text
                                )
                            }
                        }
                        BusyIndicator {
                            id: searchingIndicator
                            running: false
                            visible: running
                        }
                        Item {
                                Layout.fillWidth: true
                        }
                        Button {
                            text: "Cancel"
                            visible: searchingIndicator.running
                            onClicked: {
                                searchingIndicator.running = false
                                backend.cancel()
                            }
                        }
                    }
                    
                    ColumnLayout {
                        id: searchResultContainer
                        visible: backend.searchingPhase || backend.downloadingPhase || backend.finalPhase

                        Label {
                            text: "4. Check information about found artist/album/song:"
                            font.bold: true
                        }
                        RowLayout {
                            Image {
                                id: previewImage

                                // Use a direct link to the image
                                source: backend.previewURL
                                
                                // Optional: Show a placeholder while loading
                                asynchronous: true
                                fillMode: Image.PreserveAspectFit
                                
                                // Set a reasonable size
                                width: 120
                                height: 120
                            }
                            Label {
                                id: searchResultLabel
                                text: backend.previewText
                                textFormat: Text.RichText
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true

                            }
                            Item {
                                Layout.fillWidth: true
                            }

                            // Navigation buttons for search results
                            ColumnLayout{
                                visible: backend.searchResultCount > 1 && !(backend.downloadingPhase || backend.finalPhase)
                                
                                Button {
                                    icon.name: "go-up"
                                    onClicked: backend.previous_search_result()
                                }
                                Button {
                                    icon.name: "go-down"
                                    onClicked: backend.next_search_result()
                                }
                            }

                        }

                        // Download buttons
                        RowLayout {
                            Button {
                                id: downloadButton
                                text: "Download"
                                enabled: backend.searchingPhase
                                onClicked: {
                                    downloadLabel.text = "Retrieving information..."
                                    backend.download()
                                }
                            }

                            Item {
                                Layout.fillWidth: true
                            }
                            
                            Button {
                                text: "Cancel"
                                
                                onClicked: {
                                    backend.cancel()
                                    searchResultContainer.visible = false
                                }
                            }
                        }
                    }
                    ColumnLayout {
                        visible: backend.downloadingPhase || backend.finalPhase

                        RowLayout {
                            spacing: 8

                            // spinner
                            BusyIndicator {
                                running: backend.downloadingPhase
                                implicitWidth: 24
                                implicitHeight: 24
                            }

                            // bar
                            ProgressBar {
                                id: progressBar
                                Layout.fillWidth: true
                                from: 0
                                to: 100
                                value: 0
                            }

                            // 0% 
                            Label { text: Math.round(progressBar.value) + "%" }

                            // [3/50]
                            Label {
                                id: countLabel
                                text: "[0/0]"
                                opacity: 0.6
                            }
                        }

                        // track name
                        Label {
                            id: downloadLabel
                            text: ""
                            opacity: 0.5
                            font.italic: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight   // truncates long names with ...
                            horizontalAlignment: Text.AlignHCenter
                        }
                        Label {
                            id: errorLabel
                            visible: false
                        }


                        Connections {
                            target: backend
                            function onSearchCompleted() {
                                searchingIndicator.running = false
                                searchResultContainer.visible = true
                            }
                            function onSearchFailed(error) {
                                searchingIndicator.running = false
                                errorLabel.text = error
                                errorLabel.visible = true
                            }
                            function onProgressChanged(completed, total, trackName) {
                                progressBar.value = completed / total * 100
                                countLabel.text = "[" + completed + "/" + total + "]"
                                downloadLabel.text = trackName
                            }
                            function onDownloadFinished(common_path) {
                                downloadLabel.text = "Done!"
                                downlaodFolderButton.path  = common_path

                            }
                        }
                    }

                    ColumnLayout {
                        id: finalContainer
                        visible: backend.finalPhase
                        RowLayout {
                            Button {
                                id: downlaodFolderButton
                                text: "Open Download Music"
                                icon.name: "folder-open"
                                property string path: ""
                                onClicked: backend.open_music_folder(path)
                            }
                        }
                    }

                }
            }
    	}
    }
}
