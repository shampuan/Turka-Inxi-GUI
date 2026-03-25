import gi
import subprocess
import os
import threading
import re

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, GLib, Pango

import gettext
import locale

# Dil ayarlarını sistemden çek
try:
    locale.setlocale(locale.LC_ALL, '')
    lang = locale.getlocale()[0]
    if lang:
        lang = lang.split('_')[0]
except:
    lang = 'en'

# .mo dosyasının aranacağı yerler
locale_dirs = [
    '/usr/share/locale',
    '/usr/local/share/locale',
    os.path.join(os.path.dirname(__file__), 'locale'), # Kodun yanındaki locale klasörü
]

trans = None
for localedir in locale_dirs:
    try:
        # 'inxigui' ismi .mo dosyasının adıyla aynı olmalı
        trans = gettext.translation('inxigui', localedir=localedir, languages=[lang])
        break
    except FileNotFoundError:
        continue

if trans:
    _ = trans.gettext
else:
    _ = lambda s: s # Çeviri bulunamazsa metni olduğu gibi bırak

class InxiSadePanel(Adw.Application):
	def __init__(self):
		super().__init__(application_id='com.debian.inxi.final')
		self.aktif_buton = None

	def do_activate(self):
		self.win = Adw.ApplicationWindow(application=self)
		self.win.set_title(_("System Information Center (inxi GUI)"))

		width, height = 1050, 750
		self.win.set_default_size(width, height)

		# CSS ile Koyu Speccy Teması ve Seçili Buton Stili
		style_provider = Gtk.CssProvider()
		css_data = """
			.sidebar {
				background-color: #1e1e1e;
				border-right: 1px solid #111111;
			}
			.sidebar button {
				color: #cccccc;
				margin: 2px 8px;
				padding: 10px;
				border-radius: 4px;
				font-family: 'Liberation Sans', sans-serif;
				font-size: 10pt;
			}
			.sidebar button:hover {
				background-color: #333333;
				color: #ffffff;
			}
			/* Seçili buton (aktif kategori) stili */
			.sidebar button.suggested-action {
				background-color: #000000;
				color: #ffffff;
				font-weight: bold;
				border: 1px solid #3498db;
			}
			.report-area {
				background-color: #252525;
				color: #e0e0e0;
				font-family: 'Liberation Sans', sans-serif;
				font-size: 11pt;
			}
			.header-label {
				font-weight: bold;
				font-size: 13px;
				color: #555555;
				margin-left: 15px;
				text-transform: uppercase;
				letter-spacing: 1px;
			}
			scrolledwindow {
				background-color: #252525;
			}
		"""
		style_provider.load_from_data(css_data.encode('utf-8'))
		
		Gtk.StyleContext.add_provider_for_display(
			Gdk.Display.get_default(),
			style_provider,
			Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
		)

		ana_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.win.set_content(ana_kutu)

		header = Adw.HeaderBar()
		self.spinner = Gtk.Spinner()
		header.pack_end(self.spinner)
		
		ana_kutu.append(header)
        # Hakkında butonu
		about_btn = Gtk.Button.new_from_icon_name("help-about-symbolic")
		about_btn.set_tooltip_text(_("About"))
		about_btn.connect("clicked", self.show_about, None)
		header.pack_end(about_btn)
		paned = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		ana_kutu.append(paned)

		# SOL MENÜ
		self.sol_menu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
		self.sol_menu.set_size_request(250, -1)
		self.sol_menu.add_css_class("sidebar")
		paned.append(self.sol_menu)

		lbl_head = Gtk.Label(label=_("Components"))
		lbl_head.set_margin_top(25)
		lbl_head.set_margin_bottom(15)
		lbl_head.set_xalign(0)
		lbl_head.add_css_class("header-label")
		self.sol_menu.append(lbl_head)

		kategoriler = [
    ("🏠 " + _("System Summary"), "-b"),
    ("💻 " + _("Processor (CPU)"), "-C"),
    ("🖼️ " + _("Graphics Card (GPU)"), "-G"),
    ("💾 " + _("Memory (RAM)"), "-m"),
    ("💽 " + _("Disk Information"), "-D"),
    ("🌐 " + _("Network Cards"), "-N"),
    ("📊 " + _("Audio System"), "-A"),
    ("🌡️ " + _("Temperatures"), "-s"),
    ("📦 " + _("Software Repositories"), "-r"),
    ("🔋 " + _("Battery Status"), "-B"),
    ("📄 " + _("Full Report"), "-F")
]

		for isim, param in kategoriler:
			btn = Gtk.Button(label=isim)
			btn.set_has_frame(False)
			label = btn.get_child()
			if isinstance(label, Gtk.Label):
				label.set_xalign(0)
				label.set_margin_start(10)

			btn.param = param
			btn.connect('clicked', self.on_button_clicked)
			self.sol_menu.append(btn)

			if param == "-b":
				self.vurgula_butonu(btn)

		spacer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		spacer.set_vexpand(True)
		self.sol_menu.append(spacer)

		btn_serial = Gtk.Button(label="🔑 " + _("Serial Numbers"))
		btn_serial.set_has_frame(False)
		btn_serial.set_margin_bottom(20)
		label_s = btn_serial.get_child()
		if isinstance(label_s, Gtk.Label):
			label_s.set_xalign(0)
			label_s.set_margin_start(10)
		btn_serial.connect('clicked', self.on_serial_clicked)
		self.sol_menu.append(btn_serial)

		# SAĞ PANEL
		vbox_sag = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		vbox_sag.set_hexpand(True)
		paned.append(vbox_sag)

		scrolled = Gtk.ScrolledWindow()
		scrolled.set_vexpand(True)
		
		self.metin_alani = Gtk.TextView(editable=False)
		self.metin_alani.add_css_class("report-area")
		self.metin_alani.set_left_margin(40)
		self.metin_alani.set_right_margin(40)
		self.metin_alani.set_top_margin(40)
		self.metin_alani.set_bottom_margin(40)
		self.metin_alani.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
		self.metin_alani.set_cursor_visible(False)
		
		self.buffer = self.metin_alani.get_buffer()
		self.buffer.create_tag("bold", weight=Pango.Weight.BOLD, foreground="#3498db")
		self.buffer.create_tag("paragraf", pixels_below_lines=15)

		scrolled.set_child(self.metin_alani)
		vbox_sag.append(scrolled)

		self.win.present()
		self.islem_baslat("-b")

	def vurgula_butonu(self, buton):
		"""Önceki seçili butonu normale döndürür, yenisini koyulaştırır."""
		if self.aktif_buton:
			self.aktif_buton.remove_css_class("suggested-action")
		self.aktif_buton = buton
		self.aktif_buton.add_css_class("suggested-action")

	def on_button_clicked(self, btn):
		self.vurgula_butonu(btn)
		self.islem_baslat(btn.param)

	def on_serial_clicked(self, btn):
		self.vurgula_butonu(btn)
		self.spinner.start()
		thread = threading.Thread(target=self.arkaplan_islem_pkexec)
		thread.daemon = True
		thread.start()
		
	def show_about(self, action, param):
		about = Gtk.AboutDialog(transient_for=self.win, modal=True)
		
		# Program Kimliği
		about.set_program_name("Turka Inxi GUI")
		about.set_version("0.5.0 (beta)")
		about.set_copyright("© 2025 Bülent ERGÜN")
		
		# Açıklamalar
		about.set_comments(_("This program shows a detailed summary of your computer hardware using the inxi tool.") + 
						  "\n\n" + _("This program comes with ABSOLUTELY NO WARRANTY."))
		
		# Yazılım Bilgileri
		about.set_website("https://www.github.com/03tekno")
		about.set_website_label("Github: www.github.com/03tekno")
		about.set_authors([
			"Bülent ERGÜN (03tekno)", 
			"A. Serhat KILIÇOĞLU (www.github.com/shampuan)", 
			"Sadi YUMUŞAK (www.github.com/sadi58)"
		])
		
		about.set_license_type(Gtk.License.GPL_3_0)

		# SİSTEM İKONU BURADA TANIMLANIYOR
		# 'dialog-information' veya 'help-about' en yaygın ve şık duranlardır.
		about.set_logo_icon_name("dialog-information") 

		about.present()

	def islem_baslat(self, param):
		self.spinner.start()
		thread = threading.Thread(target=self.arkaplan_islem, args=(param,))
		thread.daemon = True
		thread.start()

	def arkaplan_islem(self, param):
		env = os.environ.copy()
		# env["LC_ALL"] = "tr_TR.UTF-8" <-- dil zorlamasına gerek yok
		try:
			res = subprocess.run(['inxi', param, '-c', '0'], capture_output=True, text=True, env=env)
			cikti = res.stdout if res.stdout else _("No data found or this hardware is not available.")
		except Exception as e:
			cikti = _("Error:") + f" {str(e)}"
		GLib.idle_add(self.metni_formatli_yaz, cikti)

	def arkaplan_islem_pkexec(self):
		try:
			komut = ['pkexec', 'inxi', '-M', '-B', '-D', '-xx', '-c', '0', '-z']
			res = subprocess.run(komut, capture_output=True, text=True, env={'LC_ALL': 'tr_TR.UTF-8'})
			cikti = res.stdout
		except:
			cikti = _("Cancel")
		GLib.idle_add(self.metni_formatli_yaz, cikti)

	def metni_formatli_yaz(self, metin):
		self.buffer.set_text("")
		satirlar = metin.split('\n')
		for satir in satirlar:
			if not satir.strip():
				continue
			match = re.match(r"^(\w+):", satir)
			iter = self.buffer.get_end_iter()
			if match:
				baslik = match.group(0)
				detay = satir[len(baslik):]
				self.buffer.insert_with_tags_by_name(iter, "\n" + baslik, "bold", "paragraf")
				iter = self.buffer.get_end_iter()
				self.buffer.insert(iter, detay + "\n")
			else:
				self.buffer.insert(iter, satir + "\n")
		self.spinner.stop()
		return False

if __name__ == "__main__":
	app = InxiSadePanel()
	app.run(None)
