#!/bin/bash

# --- DEĞİŞKENLER ---
APP_NAME="inxi-gui"
VERSION="1.0.0"
MAINTAINER="Mobilturka <github.com/03tekno>"
DESCRIPTION="inxi komutu icin modern bir grafik arayuzu."
DEPENDENCIES="python3, python3-pyqt6, inxi"
DEB_DIR="build_pkg"

echo "🚀 Paketleme işlemi başlıyor: $APP_NAME..."

# 1. Klasör Yapısını Oluştur
rm -rf $DEB_DIR
mkdir -p $DEB_DIR/DEBIAN
mkdir -p $DEB_DIR/usr/bin
mkdir -p $DEB_DIR/usr/share/$APP_NAME
mkdir -p $DEB_DIR/usr/share/applications
mkdir -p $DEB_DIR/usr/share/pixmaps

# 2. Kontrol Dosyasını Oluştur (Control File)
cat <<EOF > $DEB_DIR/DEBIAN/control
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Maintainer: $MAINTAINER
Depends: $DEPENDENCIES
Description: $DESCRIPTION
EOF

# 3. Python Dosyasını ve Gerekli Dosyaları Kopyala
cp inxi.py $DEB_DIR/usr/share/$APP_NAME/main.py

# Eğer klasörde icon.png varsa kopyala, yoksa sistem ikonunu kullanması için boş geç
if [ -f "icon.png" ]; then
    cp icon.png $DEB_DIR/usr/share/pixmaps/$APP_NAME.png
    ICON_PATH=$APP_NAME
else
    ICON_PATH="utilities-terminal"
fi

# 4. Çalıştırılabilir Başlatıcı (Launcher) Oluştur
cat <<EOF > $DEB_DIR/usr/bin/$APP_NAME
#!/bin/bash
python3 /usr/share/$APP_NAME/main.py "\$@"
EOF
chmod +x $DEB_DIR/usr/bin/$APP_NAME

# 5. Masaüstü Kısayolu (Desktop Entry) Oluştur
cat <<EOF > $DEB_DIR/usr/share/applications/$APP_NAME.desktop
[Desktop Entry]
Name=Sistem Bilgi Merkezi
Comment=$DESCRIPTION
Exec=$APP_NAME
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=System;
EOF

# 6. Paketi Oluştur
dpkg-deb --build $DEB_DIR "${APP_NAME}_${VERSION}_all.deb"

# Temizlik
rm -rf $DEB_DIR

echo "✅ İşlem tamamlandı! ${APP_NAME}_${VERSION}_all.deb dosyası oluşturuldu."