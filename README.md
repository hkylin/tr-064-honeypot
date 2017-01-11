# tr-064-honeypot 

# Install Scripts  
apt-get update  
apt-get -y install git python-pip supervisor  
pip install virtualenv  

# Get the tr-064-honeypot source  
cd /opt  
git clone https://github.com/zom3y3/tr-064-honeypot.git  
cd tr-064-honeypot  
mkdir sample  

virtualenv env  
. env/bin/activate  
pip install -r requirements.txt  

# Config for supervisor.  
cat > /etc/supervisor/conf.d/tr-064-honeypot.conf <<EOF  
[program:tr-064-honeypot]  
command=/opt/tr-064-honeypot/env/bin/python /opt/tr-064-honeypot/tr-064.py   
directory=/opt/tr-064-honeypot  
stdout_logfile=/opt/tr-064-honeypot/tr-064.out  
stderr_logfile=/opt/tr-064-honeypot/tr-064.err  
autostart=true  
autorestart=true  
redirect_stderr=true  
stopsignal=QUIT  
EOF  

supervisorctl update

