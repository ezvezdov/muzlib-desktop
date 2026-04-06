import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

TextArea {
    id: control

    // Defaults for text areas
    Layout.fillWidth: true
    wrapMode: Text.WrapAnywhere

    // Navigation logic
    Keys.onTabPressed: (event) => {
        nextItemInFocusChain(true).forceActiveFocus(Qt.TabFocusReason)
        event.accepted = true
    }

    Keys.onBacktabPressed: (event) => {
        nextItemInFocusChain(false).forceActiveFocus(Qt.BacktabFocusReason)
        event.accepted = true
    }
}
