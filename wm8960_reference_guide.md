# Waveshare WM8960 Audio Bonnet - Reference Guide
*Raspberry Pi 5 Configuration*

## 🎯 Quick Start Commands

### Volume Control
```bash
# Digital volume (0-100%)
amixer -c 0 set 'Playback' 85%

# Speaker volume (0-100%) 
amixer -c 0 set 'Speaker' 85%

# Headphone volume (0-100%)
amixer -c 0 set 'Headphone' 80%

# Microphone input (0-100%)
amixer -c 0 set 'Capture' 50%
```

### Audio Testing
```bash
# Basic audio test
speaker-test -D hw:0,0 -c2 -t sine -f 440

# Play audio file
aplay -D hw:0,0 your_file.wav

# Check audio devices
aplay -l

# View all mixer controls
amixer -c 0 scontrols
```

## 🔧 Configuration Files

### /boot/firmware/config.txt
```bash
# Required settings for WM8960
dtparam=i2c_arm=on
dtparam=i2s=on
dtparam=audio=off
dtoverlay=wm8960-soundcard
```

### /etc/asound.conf (Optional - for software mixing)
```bash
pcm.!default {
    type plug
    slave.pcm "dmixed"
}

ctl.!default {
    type hw
    card 0
}

pcm.dmixed {
    type dmix
    ipc_key 1024
    slave {
        pcm "hw:0,0"
        rate 44100
        channels 2
        format S16_LE
        period_size 1024
        buffer_size 4096
    }
    bindings {
        0 0
        1 1
    }
}
```

## 🐍 Python Usage

### Pygame Configuration
```python
import pygame

# Initialize with optimal settings for WM8960
pygame.mixer.pre_init(
    frequency=44100,
    size=-16,
    channels=2,
    buffer=1024
)
pygame.mixer.init()
```

### Direct ALSA Access
```python
import subprocess

# Play file with direct hardware access
subprocess.run(['aplay', '-D', 'hw:0,0', 'sound.wav'])

# Set volume from Python
subprocess.run(['amixer', '-c', '0', 'set', 'Playback', '85%'])
```

## 🔍 Troubleshooting

### No Sound Issues
1. **Check connections**: Ensure speakers/headphones connected to correct jack
2. **Check volume**: All three volume controls must be set (Playback, Speaker, Headphone)
3. **Check device**: `aplay -l` should show wm8960-soundcard
4. **Test direct**: `speaker-test -D hw:0,0 -c2 -t sine`

### ALSA Configuration Errors
```bash
# Remove problematic configs
sudo rm -f /etc/asound.conf
sudo rm -f ~/.asoundrc

# Test without config
aplay -l
```

### Permission Issues
```bash
# Add user to audio group
sudo usermod -a -G audio $USER

# Reboot after adding to group
sudo reboot
```

### Device Tree Issues
```bash
# Check overlays are loaded
dmesg | grep -i wm8960

# Alternative overlay
sudo sed -i 's/wm8960-soundcard/wm8960-soundcard,addr=0x1a/' /boot/firmware/config.txt
```

## 📊 Optimal Settings

### Volume Levels
- **Playback (Digital)**: 85% - Main volume control
- **Speaker**: 85% - For speaker output  
- **Headphone**: 80% - For headphone output
- **Capture**: 50% - For microphone input

### Audio Parameters
- **Sample Rate**: 44100 Hz (optimal for WM8960)
- **Format**: S16_LE (16-bit signed little endian)
- **Channels**: 2 (stereo)
- **Buffer Size**: 1024-4096 samples

### Important Mixer Settings
```bash
# Enable PCM output routing (essential!)
amixer -c 0 set 'Left Output Mixer PCM' on
amixer -c 0 set 'Right Output Mixer PCM' on

# Save settings permanently
sudo alsactl store
```

## 🎵 Audio Specifications

- **Codec**: WM8960 24-bit
- **Sample Rates**: 8kHz to 48kHz
- **Channels**: Stereo output + mono microphone input
- **Output Power**: 1W per channel (speaker)
- **I2C Address**: 0x1a
- **Interface**: I2S

## 🔄 Maintenance Commands

```bash
# Save current mixer settings
sudo alsactl store

# Restore saved settings
sudo alsactl restore

# Reset to defaults
sudo alsactl init

# View detailed device info
cat /proc/asound/cards
cat /proc/asound/devices
```

## 🚨 Emergency Reset

If audio completely breaks:

```bash
# 1. Remove all configs
sudo rm -f /etc/asound.conf
sudo rm -f ~/.asoundrc

# 2. Reset ALSA
sudo alsactl init

# 3. Reboot
sudo reboot

# 4. Test basic functionality
aplay -l
speaker-test -D hw:0,0 -c2 -t sine
```

---

**✅ Migration from Adafruit to Waveshare WM8960 Complete!**

*Your Raspberry Pi 5 is now configured for optimal audio performance with the Waveshare WM8960 Audio Bonnet.*