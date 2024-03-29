#!/bin/bash
#
# Install, enable and run the Example-Python-Daemon.service with systemd
# as a user service.
# 
# This does
# Paul Grimes
# 06/29/2023
#

INSTALL="$HOME/.config/systemd/example-smax-daemon"

mkdir -p $INSTALL

cp "./example-smax-daemon.py" $INSTALL
cp "./example-smax-daemon.service" $INSTALL
cp "./on-start.sh" $INSTALL

chmod -R 755 $INSTALL

ln -s "$INSTALL/example-smax-daemon.service" "$HOME/.config/systemd/user/example-smax-daemon.service"

read -p "Enable example-smax-daemon at this time? " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    systemctl --user daemon-reload
    systemctl --user enable example-smax-daemon
    systemctl --user restart example-smax-daemon
fi

exit