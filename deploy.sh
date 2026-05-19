#!/bin/bash
cd /home/ubuntu/ve_database
python3 -c "import zipfile, os; z=zipfile.ZipFile('images.zip'); [z.extract(f, 'data/images/') for f in z.namelist()]"
git pull origin master
pm2 restart ve-dashboard
