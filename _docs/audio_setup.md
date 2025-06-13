# Bedrock Audio System Setup Guide

Complete automated setup for Bedrock audio system on Raspberry Pi with USB audio devices.

## 📋 Overview

This setup configures your system for optimal audio performance by:
- Completely removing PulseAudio conflicts
- Configuring ALSA for direct USB audio access
- Installing all required dependencies
- Setting up Python environment for Bedrock
- Creating comprehensive test utilities

## 🎯 Target Systems

**Primary Target:**
- Raspberry Pi 4/5 with Raspberry Pi OS
- USB audio devices (GS3, dongles, USB headsets)
- Fresh/clean installations

**Also Works On:**
- Other ARM-based Linux systems
- Debian/Ubuntu x86/x64 systems
- Systems with existing audio setups (will be reconfigured)

## 📦 What's Included

### Setup Scripts
1. **`system_check.sh`** - Pre-setup system requirements check
2. **`bedrock_audio_setup.sh`** - Main setup script
3. **`test_audio_system.py`** - Comprehensive audio testing
4. **`quick_audio_test.sh`** - Quick audio verification

### Configurations Created
- `~/.asoundrc` - ALSA configuration for USB audio
- `~/.config/pulse/*` - PulseAudio disable configuration
- `~/.bashrc` - Environment variables for audio system
- Systemd overrides to prevent PulseAudio

## 🚀 Quick Start

### Step 1: Download Scripts

```bash
# Method 1: Download individual scripts
curl -O https://[your-server]/system_check.sh
curl -O https://[your-server]/bedrock_audio_setup.sh

# Method 2: Create scripts from documentation
# (Copy-paste the script contents from artifacts above)

# Make executable
chmod +x system_check.sh bedrock_audio_setup.sh
```

### Step 2: Check System Requirements

```bash
./system_check.sh
```

This will verify:
- ✅ OS compatibility (Debian-based preferred)
- ✅ Hardware detection (Raspberry Pi optimization)
- ✅ Python 3.8+ availability
- ✅ Audio hardware detection
- ✅ Network connectivity
- ✅ Sufficient storage space

### Step 3: Run Main Setup

```bash
./bedrock_audio_setup.sh
```

The setup will:
1. Update system packages
2. Install audio and development packages
3. Remove PulseAudio completely
4. Configure ALSA for USB audio
5. Set up environment variables
6. Install Python dependencies
7. Create test utilities

### Step 4: Reboot and Test

```bash
sudo reboot

# After reboot, test the setup
~/quick_audio_test.sh

# Or run comprehensive test
python3 ~/test_audio_system.py
```

## 🔧 Detailed Setup Process

### Pre-Installation

1. **Fresh System Recommended**: While the setup works on existing systems, a fresh Raspberry Pi OS installation gives best results.

2. **USB Audio Device**: Connect your USB audio device (GS3, USB dongle, etc.) before running setup.

3. **Network Connection**: Required for downloading packages.

4. **Sudo Access**: User must have sudo privileges.

### Installation Steps

The main setup script performs these operations:

#### System Updates
```bash
sudo apt update && sudo apt upgrade -y
```

#### Package Installation
- **Audio**: alsa-utils, alsa-tools, libasound2-dev
- **Python**: python3-pip, python3-venv, python3-dev
- **Raspberry Pi**: python3-lgpio, i2c-tools
- **Development**: build-essential, git, curl
- **Multimedia**: ffmpeg, libsdl2-dev

#### PulseAudio Removal
- Stops all PulseAudio processes
- Removes PulseAudio packages completely
- Cleans configuration directories
- Prevents auto-restart via systemd

#### ALSA Configuration
Creates `~/.asoundrc` with:
- USB audio as default device (card 1/2)
- Fallback configurations for different card positions
- Format conversion and routing
- HDMI audio as backup

#### Environment Setup
Adds to `~/.bashrc`:
```bash
export SDL_AUDIODRIVER=alsa
export PULSE_RUNTIME_PATH=/run/user/$(id -u)/pulse-dummy
export PULSE_STATE_PATH=/run/user/$(id -u)/pulse-dummy
export PULSE_DISABLED=1
export ALSA_CARD=1
export PYGAME_HIDE_SUPPORT_PROMPT=1
```

#### Python Dependencies
Installs Bedrock requirements:
- kivy, kivymd (UI framework)
- pygame, pyalsaaudio (audio)
- Raspberry Pi GPIO libraries
- Sensor libraries (I2C, environmental)
- Network and utility libraries

## 🧪 Testing Your Setup

### Quick Test
```bash
~/quick_audio_test.sh
```
Output example:
```
🔍 Quick Audio Test
==================
📋 Audio cards:
card 0: vc4hdmi0 [vc4-hdmi-0], device 0: MAI PCM i2s-hifi-0
card 1: GS3 [GS3], device 0: USB Audio [USB Audio]

🎵 Testing default audio (3 seconds):
✅ Audio test completed

🌍 Environment:
   SDL_AUDIODRIVER: alsa
   PULSE_DISABLED: 1

🚫 PulseAudio processes:
✅ PulseAudio not running
```

### Comprehensive Test
```bash
python3 ~/test_audio_system.py
```
Tests:
- ✅ Environment variables
- ✅ ALSA configuration and devices
- ✅ PulseAudio disabled status
- ✅ Pygame audio initialization
- ✅ Sound generation capabilities

### Expected Results
After successful setup, you should see:
- No PulseAudio error messages
- USB audio device detected as default
- Pygame initializes without warnings
- Sound tests complete successfully

## 🔄 Post-Setup: Bedrock Application

### Option 1: New Bedrock Project
```bash
# Create project directory
mkdir ~/bedrock-app
cd ~/bedrock-app

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Clone/download your Bedrock application
git clone [your-bedrock-repo] .

# Install additional dependencies
pip install -r requirements.txt

# Run application
python3 main.py
```

### Option 2: Existing Bedrock Project
```bash
cd ~/bedrock-app
source .venv/bin/activate

# Update environment
source ~/.bashrc

# Test audio services
python3 -c "from services.volume_service import VolumeControlService; VolumeControlService().diagnose_audio_system()"

# Run application
python3 main.py
```

## 🛠️ Troubleshooting

### Common Issues

**1. USB Audio Not Detected**
```bash
# Check USB devices
lsusb | grep -i audio

# Check ALSA cards
aplay -l

# Manually test USB audio
aplay -D hw:1,0 /usr/share/sounds/alsa/Front_Left.wav
```

**2. Environment Variables Not Set**
```bash
# Reload bashrc
source ~/.bashrc

# Check variables
env | grep -E "(SDL_|PULSE_|ALSA_)"

# Manual export if needed
export SDL_AUDIODRIVER=alsa
```

**3. PulseAudio Still Running**
```bash
# Kill processes
pulseaudio -k
pkill -9 pulseaudio

# Check systemd services
systemctl --user status pulseaudio.service
systemctl --user mask pulseaudio.service pulseaudio.socket
```

**4. Pygame Initialization Fails**
```bash
# Test pygame directly
python3 -c "import pygame; pygame.mixer.init(); print('Success')"

# Check SDL audio driver
python3 -c "import os; os.environ['SDL_AUDIODRIVER']='alsa'; import pygame; pygame.mixer.init()"
```

### Diagnostic Commands

```bash
# Audio system overview
~/quick_audio_test.sh

# Detailed diagnostics
python3 ~/test_audio_system.py

# Manual checks
aplay -l                    # List audio devices
cat ~/.asoundrc            # Check ALSA config
pgrep pulseaudio           # Check PulseAudio processes
env | grep PULSE           # Check environment
systemctl --user list-units | grep pulse  # Check systemd
```

### Reset Audio Configuration

If you need to start over:
```bash
# Remove configurations
rm ~/.asoundrc
rm -rf ~/.config/pulse

# Remove environment variables
sed -i '/BEDROCK AUDIO/,/^$/d' ~/.bashrc

# Reinstall PulseAudio (if desired)
sudo apt install pulseaudio

# Re-run setup
./bedrock_audio_setup.sh
```

## 📚 Advanced Configuration

### Custom USB Audio Device

If your USB device isn't auto-detected, modify `~/.asoundrc`:
```bash
# Find your device
aplay -l

# Edit configuration
nano ~/.asoundrc

# Change card number/name to match your device
pcm.!default {
    type plug
    slave {
        pcm "hw:X,0"        # Replace X with your card number
        rate 44100
        channels 2
        format S16_LE
    }
}
```

### Multiple Audio Devices

To support multiple USB audio devices:
```bash
# Add to ~/.asoundrc
pcm.usb1 {
    type hw
    card 1
    device 0
}

pcm.usb2 {
    type hw
    card 2  
    device 0
}

# Use in Bedrock configuration
# Set device preference in your application
```

### Performance Tuning

For better audio performance:
```bash
# Add to ~/.bashrc
export ALSA_PERIOD_SIZE=1024
export ALSA_BUFFER_SIZE=4096

# GPU memory split (Raspberry Pi only)
sudo raspi-config
# Advanced Options > Memory Split > 128
```

## 📖 Understanding the Setup

### Why Remove PulseAudio?

PulseAudio adds complexity and latency for embedded applications:
- **Direct Hardware Access**: ALSA provides direct access to audio hardware
- **Lower Latency**: Eliminates PulseAudio processing overhead
- **Better Control**: Fine-grained control over audio routing and mixing
- **Stability**: Fewer moving parts, fewer potential conflicts
- **Raspberry Pi Optimization**: ALSA is more efficient on resource-constrained systems

### ALSA Configuration Explained

The `~/.asoundrc` file defines:
- **Default PCM Device**: Where audio output goes by default
- **Plugin Chain**: Format conversion, routing, mixing
- **Device Aliases**: Named shortcuts for different audio devices
- **Fallback Options**: Multiple configuration options for different hardware setups

### Environment Variables

- `SDL_AUDIODRIVER=alsa`: Forces SDL (pygame) to use ALSA
- `PULSE_RUNTIME_PATH=/dev/null`: Prevents PulseAudio runtime directory creation
- `PULSE_DISABLED=1`: Application-level PulseAudio disable flag
- `ALSA_CARD=1`: Default ALSA card for applications that support it

## 🎯 Best Practices

### For Production Systems
1. **Test Thoroughly**: Run all test scripts before deploying
2. **Document Changes**: Note any custom modifications
3. **Backup Configurations**: Save working configurations
4. **Monitor Performance**: Check audio latency and CPU usage
5. **Update Regularly**: Keep system packages updated

### For Development
1. **Use Virtual Environments**: Isolate Python dependencies
2. **Version Control**: Track configuration changes
3. **Test on Target Hardware**: Always test on actual Raspberry Pi
4. **Log Audio Events**: Implement comprehensive audio logging
5. **Handle Failures Gracefully**: Implement fallback audio options

## 🤝 Support

If you encounter issues:

1. **Run Diagnostics**: Use provided test scripts
2. **Check Logs**: Review system and application logs
3. **Verify Hardware**: Ensure USB audio device is working
4. **Test Step-by-Step**: Isolate the failing component
5. **Document Issues**: Note exact error messages and system details

## 📝 Changelog

### Version 1.0
- Initial release
- Raspberry Pi 4/5 support
- USB audio optimization
- Complete PulseAudio removal
- Comprehensive testing suite

---

*This setup is specifically designed for Bedrock applications on Raspberry Pi with USB audio devices. It provides a clean, optimized audio environment for embedded applications.*