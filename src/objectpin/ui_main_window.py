# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QProgressBar, QPushButton, QSizePolicy, QSpinBox,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1180, 760)
        MainWindow.setMinimumSize(QSize(980, 640))
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.rootLayout = QHBoxLayout(self.centralwidget)
        self.rootLayout.setSpacing(12)
        self.rootLayout.setObjectName(u"rootLayout")
        self.rootLayout.setContentsMargins(14, 14, 14, 14)
        self.imageFrame = QFrame(self.centralwidget)
        self.imageFrame.setObjectName(u"imageFrame")
        self.imageFrame.setFrameShape(QFrame.Shape.StyledPanel)
        self.imageLayout = QVBoxLayout(self.imageFrame)
        self.imageLayout.setObjectName(u"imageLayout")
        self.imageLayout.setContentsMargins(0, 0, 0, 0)
        self.imageLabel = QLabel(self.imageFrame)
        self.imageLabel.setObjectName(u"imageLabel")
        self.imageLabel.setMinimumSize(QSize(560, 420))
        self.imageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.imageLayout.addWidget(self.imageLabel)


        self.rootLayout.addWidget(self.imageFrame)

        self.controlPanel = QFrame(self.centralwidget)
        self.controlPanel.setObjectName(u"controlPanel")
        self.controlPanel.setMinimumSize(QSize(340, 0))
        self.controlPanel.setMaximumSize(QSize(380, 16777215))
        self.controlPanel.setFrameShape(QFrame.Shape.NoFrame)
        self.controlLayout = QVBoxLayout(self.controlPanel)
        self.controlLayout.setSpacing(10)
        self.controlLayout.setObjectName(u"controlLayout")
        self.controlLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setSpacing(8)
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.openButton = QPushButton(self.controlPanel)
        self.openButton.setObjectName(u"openButton")

        self.buttonLayout.addWidget(self.openButton)

        self.runButton = QPushButton(self.controlPanel)
        self.runButton.setObjectName(u"runButton")
        self.runButton.setEnabled(False)

        self.buttonLayout.addWidget(self.runButton)


        self.controlLayout.addLayout(self.buttonLayout)

        self.taskLabel = QLabel(self.controlPanel)
        self.taskLabel.setObjectName(u"taskLabel")

        self.controlLayout.addWidget(self.taskLabel)

        self.taskCombo = QComboBox(self.controlPanel)
        self.taskCombo.addItem("")
        self.taskCombo.addItem("")
        self.taskCombo.addItem("")
        self.taskCombo.addItem("")
        self.taskCombo.setObjectName(u"taskCombo")

        self.controlLayout.addWidget(self.taskCombo)

        self.queryLabel = QLabel(self.controlPanel)
        self.queryLabel.setObjectName(u"queryLabel")

        self.controlLayout.addWidget(self.queryLabel)

        self.queryEdit = QLineEdit(self.controlPanel)
        self.queryEdit.setObjectName(u"queryEdit")

        self.controlLayout.addWidget(self.queryEdit)

        self.settingsGrid = QGridLayout()
        self.settingsGrid.setObjectName(u"settingsGrid")
        self.settingsGrid.setHorizontalSpacing(8)
        self.settingsGrid.setVerticalSpacing(8)
        self.maxSideLabel = QLabel(self.controlPanel)
        self.maxSideLabel.setObjectName(u"maxSideLabel")

        self.settingsGrid.addWidget(self.maxSideLabel, 0, 0, 1, 1)

        self.maxSideSpin = QSpinBox(self.controlPanel)
        self.maxSideSpin.setObjectName(u"maxSideSpin")
        self.maxSideSpin.setMinimum(256)
        self.maxSideSpin.setMaximum(1600)
        self.maxSideSpin.setSingleStep(64)
        self.maxSideSpin.setValue(512)

        self.settingsGrid.addWidget(self.maxSideSpin, 0, 1, 1, 1)

        self.modeLabel = QLabel(self.controlPanel)
        self.modeLabel.setObjectName(u"modeLabel")

        self.settingsGrid.addWidget(self.modeLabel, 1, 0, 1, 1)

        self.modeCombo = QComboBox(self.controlPanel)
        self.modeCombo.addItem("")
        self.modeCombo.addItem("")
        self.modeCombo.addItem("")
        self.modeCombo.setObjectName(u"modeCombo")

        self.settingsGrid.addWidget(self.modeCombo, 1, 1, 1, 1)

        self.tokensLabel = QLabel(self.controlPanel)
        self.tokensLabel.setObjectName(u"tokensLabel")

        self.settingsGrid.addWidget(self.tokensLabel, 2, 0, 1, 1)

        self.tokensSpin = QSpinBox(self.controlPanel)
        self.tokensSpin.setObjectName(u"tokensSpin")
        self.tokensSpin.setMinimum(32)
        self.tokensSpin.setMaximum(8192)
        self.tokensSpin.setSingleStep(32)
        self.tokensSpin.setValue(256)

        self.settingsGrid.addWidget(self.tokensSpin, 2, 1, 1, 1)


        self.controlLayout.addLayout(self.settingsGrid)

        self.progressBar = QProgressBar(self.controlPanel)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setMaximum(1)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)

        self.controlLayout.addWidget(self.progressBar)

        self.statusLabel = QLabel(self.controlPanel)
        self.statusLabel.setObjectName(u"statusLabel")
        self.statusLabel.setWordWrap(True)

        self.controlLayout.addWidget(self.statusLabel)

        self.outputEdit = QTextEdit(self.controlPanel)
        self.outputEdit.setObjectName(u"outputEdit")
        self.outputEdit.setReadOnly(True)

        self.controlLayout.addWidget(self.outputEdit)


        self.rootLayout.addWidget(self.controlPanel)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"ObjectPin", None))
        self.imageLabel.setText(QCoreApplication.translate("MainWindow", u"Open an image", None))
        self.openButton.setText(QCoreApplication.translate("MainWindow", u"Open", None))
        self.runButton.setText(QCoreApplication.translate("MainWindow", u"Run", None))
        self.taskLabel.setText(QCoreApplication.translate("MainWindow", u"Task", None))
        self.taskCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"Detect categories", None))
        self.taskCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"Ground phrase", None))
        self.taskCombo.setItemText(2, QCoreApplication.translate("MainWindow", u"Point to phrase", None))
        self.taskCombo.setItemText(3, QCoreApplication.translate("MainWindow", u"Detect text", None))

        self.queryLabel.setText(QCoreApplication.translate("MainWindow", u"Query", None))
        self.queryEdit.setText(QCoreApplication.translate("MainWindow", u"person, car, bicycle", None))
        self.maxSideLabel.setText(QCoreApplication.translate("MainWindow", u"Max side", None))
        self.modeLabel.setText(QCoreApplication.translate("MainWindow", u"Mode", None))
        self.modeCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"fast", None))
        self.modeCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"hybrid", None))
        self.modeCombo.setItemText(2, QCoreApplication.translate("MainWindow", u"slow", None))

        self.tokensLabel.setText(QCoreApplication.translate("MainWindow", u"Tokens", None))
        self.statusLabel.setText(QCoreApplication.translate("MainWindow", u"Loading model...", None))
        self.outputEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Model output", None))
    # retranslateUi

