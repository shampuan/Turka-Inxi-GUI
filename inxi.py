import sys
import subprocess
import threading
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTextEdit, QLabel, QFrame, QLineEdit, QDialog,
    QProgressBar, QGraphicsDropShadowEffect, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QScreen

class WorkerSignals(QObject):
    result_ready = pyqtSignal(str)

class ModernInxi(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistem Bilgi Merkezi (inxi-gui")
        self.resize(1100, 750)
        
        # --- BAŞLANGIÇ AYARI: Açık ---
        self.is_dark = False 
        
        self.signals = WorkerSignals()
        self.signals.result_ready.connect(self.display_data)
        
        self.init_ui()
        # --- İKON AYARI ---
        # Eğer 'icon.png' dosyan varsa alttaki satırı kullanabilirsin:
        # self.setWindowIcon(QIcon("icon.png"))
        # Yoksa sistemin varsayılan bilgisayar ikonunu kullanır:
        self.setWindowIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        self.apply_theme()
        self.center_window() # Ekran ortalama
        
        self.run_command("-b")

    def center_window(self):
        """Pencereyi ekranın tam ortasına yerleştirir."""
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- SOL PANEL ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(260)
        self.sidebar.setObjectName("sidebar")
        sidebar_vbox = QVBoxLayout(self.sidebar)
        
        title = QLabel("  Sistemim")
        title.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        title.setStyleSheet("margin: 20px 0px; color: #3d5afe; padding-left: 10px;")
        sidebar_vbox.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_content = QWidget()
        self.btns_layout = QVBoxLayout(scroll_content)
        self.btns_layout.setContentsMargins(10, 0, 10, 0)
        self.btns_layout.setSpacing(6)

        kategoriler = [
            ("🏠 Sistem Özeti", "-b"), ("💻 İşlemci (CPU)", "-C"),
            ("🖼️ Ekran Kartı (GPU)", "-G"), ("💾 Bellek (RAM)", "-m"),
            ("💽 Disk Bilgisi", "-D"), ("🌐 Ağ Kartları", "-N"),
            ("📊 Ses Sistemi", "-A"), ("🌡️ Sıcaklıklar", "-s"),
            ("📦 Yazılım Depoları", "-r"), ("🔋 Pil Durumu", "-B")
        ]

        self.btns = []
        for text, param in kategoriler:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.param = param
            btn.clicked.connect(lambda ch, b=btn: self.on_btn_click(b))
            self.btns_layout.addWidget(btn)
            self.btns.append(btn)

        self.serial_btn = QPushButton("🔑 Seri Numaraları")
        self.serial_btn.setObjectName("serialBtn")
        self.serial_btn.setFixedHeight(40)
        self.serial_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.serial_btn.clicked.connect(self.request_sudo)
        self.btns_layout.addWidget(self.serial_btn)

        btn_report = QPushButton("📄 Tam Rapor")
        btn_report.setCheckable(True)
        btn_report.setFixedHeight(40)
        btn_report.param = "-Fxxxpmr"
        btn_report.clicked.connect(lambda ch, b=btn_report: self.on_btn_click(b))
        self.btns_layout.addWidget(btn_report)
        self.btns.append(btn_report)

        self.btns_layout.addStretch()
        scroll.setWidget(scroll_content)
        sidebar_vbox.addWidget(scroll)

        self.theme_btn = QPushButton("🌙 Karanlık Moda Geç")
        self.theme_btn.clicked.connect(self.toggle_theme)
        sidebar_vbox.addWidget(self.theme_btn)

        # --- SAĞ PANEL ---
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(30, 20, 30, 30)

        self.status_label = QLabel("Hazır")
        self.status_label.setStyleSheet("font-size: 11px; color: gray;")
        right_layout.addWidget(self.status_label)

        self.loader = QProgressBar()
        self.loader.setRange(0, 0)
        self.loader.setFixedHeight(3)
        self.loader.setTextVisible(False)
        self.loader.hide()
        right_layout.addWidget(self.loader)

        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(QFont("Monospace", 10))
        self.text_display.setObjectName("console")
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 5)
        self.text_display.setGraphicsEffect(shadow)
        right_layout.addWidget(self.text_display)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(right_panel)

    def apply_theme(self):
        if self.is_dark:
            bg, fg, side, card, hover = "#111114", "#e1e1e6", "#19191c", "#1e1e24", "#2a2a30"
            self.theme_btn.setText("☀️ Aydınlık Moda Geç")
        else:
            # AYDINLIK MOD RENKLERİ
            bg, fg, side, card, hover = "#f8f9fa", "#2d3436", "#ffffff", "#ffffff", "#e9ecef"
            self.theme_btn.setText("🌙 Karanlık Moda Geç")
        
        accent = "#3d5afe"

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {bg}; color: {fg}; }}
            #sidebar {{ background-color: {side}; border-right: 1px solid {hover}; }}
            QPushButton {{
                text-align: left; padding-left: 15px; border-radius: 8px;
                background-color: transparent; border: none; font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:checked {{ background-color: {accent}; color: white; }}
            #console {{
                background-color: {card}; color: {fg};
                border: 1px solid {hover}; border-radius: 12px; padding: 15px;
            }}
            #serialBtn {{ color: #e67e22; font-weight: bold; border: 1px solid rgba(230,126,34,0.2); }}
            QScrollBar:vertical {{ width: 8px; background: transparent; }}
            QScrollBar::handle:vertical {{ background: {accent}; border-radius: 4px; min-height: 20px; }}
        """)

    def on_btn_click(self, target_btn):
        for btn in self.btns: btn.setChecked(False)
        target_btn.setChecked(True)
        self.run_command(target_btn.param)

    def run_command(self, param):
        self.loader.show()
        self.status_label.setText("Sistem taranıyor...")
        threading.Thread(target=self._worker, args=(param,), daemon=True).start()

    def _worker(self, param):
        env = os.environ.copy()
        env["LC_ALL"] = "tr_TR.UTF-8"
        res = subprocess.run(['inxi', param, '-c', '0'], capture_output=True, text=True, env=env)
        self.signals.result_ready.emit(res.stdout if res.stdout else "Veri bulunamadı.")

    def display_data(self, data):
        self.loader.hide()
        self.status_label.setText("Güncellendi")
        self.text_display.setPlainText(data)

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.apply_theme()

    def request_sudo(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Güvenli Erişim")
        l = QVBoxLayout(dialog)
        l.addWidget(QLabel("🔑 Sudo Şifresi:"))
        pw = QLineEdit(); pw.setEchoMode(QLineEdit.EchoMode.Password)
        l.addWidget(pw); b = QPushButton("Tamam"); b.clicked.connect(dialog.accept); l.addWidget(b)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.loader.show()
            threading.Thread(target=self._sudo_worker, args=(pw.text(),), daemon=True).start()

    def _sudo_worker(self, password):
        cmd = f"echo '{password}' | sudo -S script -qec 'inxi -M -B -c 0' /dev/null"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        lines = [l.strip() for l in res.stdout.split('\n') if 'serial:' in l.lower()]
        self.signals.result_ready.emit("\n".join(lines) if lines else "Seri no bulunamadı.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernInxi()
    window.show()
    sys.exit(app.exec())