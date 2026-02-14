#!/bin/bash


rm app.db
wget -O app.db https://github.com/iiab/iiab/raw/refs/heads/master/roles/calibre-web/files/app.db
sudo chown $(whoami) app.db
sudo rm -r /library/
sudo mkdir -p /library/calibre-web
sudo mkdir /library/downloads/
sudo wget -O /library/calibre-web/metadata.db https://github.com/iiab/iiab/raw/refs/heads/master/roles/calibre-web/files/metadata.db
sudo chown $(whoami) /library/calibre-web
sudo chown $(whoami) /library/calibre-web/metadata.db
sudo chown $(whoami) /library/downloads/
