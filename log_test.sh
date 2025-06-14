#!/bin/bash
sudo systemctl stop kivy-app
sudo truncate -s 0 app.log
sudo systemctl start kivy-app
sleep 5
sudo systemctl stop kivy-app

