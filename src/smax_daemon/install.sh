#!/bin/bash
#
# Install, enable and run the Example-Python-Daemon.service with systemd
# as a user service.
# 
# This does
# Paul Grimes
# 06/29/2023
#

USR_LOCAL_LIB="/usr/local/lib"
INSTALL="$USR_LOCAL_LIB/example_smax_daemon"
CONFIG="/home/smauser/wsma_config"

mkdir -p $INSTALL
mkdir -p "$CONFIG/example_smax_daemon"

cp "./example_smax_daemon.py" $INSTALL
cp "./example_smax_daemon.service" $INSTALL
cp "./on_start.sh" $INSTALL

chmod -R 755 $INSTALL
chown -R smauser:smauser $INSTALL

ln -s "$INSTALL/example_smax_daemon.service" "/etc/systemd/system/example_smax_daemon.service"

if ! test -f "$CONFIG/smax_config.json"
then
    cp "./smax_config.json" "$CONFIG"
fi
cp "./daemon_config.json" "$CONFIG/example_smax_daemon"

read -p "Enable example_smax_daemon at this time? " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    systemctl daemon-reload
    systemctl enable example_smax_daemon
    systemctl restart example_smax_daemon
fi

exit