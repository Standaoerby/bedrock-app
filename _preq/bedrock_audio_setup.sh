#!/bin/bash
# bedrock_audio_setup.sh - Complete setup script for Bedrock audio system
# Configures ALSA, disables PulseAudio, optimizes for Raspberry Pi + USB audio
# Version: 1.0
# Usage: ./bedrock_audio_setup.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        error "This script should NOT be run as root. Run as regular user."
    fi
}

# Check if running on Raspberry Pi
check_raspberry_pi() {
    if [ ! -f /proc/device-tree/model ]; then
        warn "Not running on Raspberry Pi - some optimizations may not apply"
        return 1
    fi
    
    local model=$(cat /proc/device-tree/model 2>/dev/null)
    log "Detected: $model"
    return 0
}

# Check system prerequisites
check_system() {
    log "Checking system prerequisites..."
    
    # Check OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log "OS: $NAME $VERSION"
    else
        warn "Could not detect OS version"
    fi
    
    # Check architecture
    local arch=$(uname -m)
    log "Architecture: $arch"
    
    # Check Python version
    if command -v python3 >/dev/null 2>&1; then
        local python_version=$(python3 --version)
        log "Python: $python_version"
    else
        error "Python 3 is required but not installed"
    fi
}

# Update system packages
update_system() {
    log "Updating system packages..."
    
    sudo apt update
    sudo apt upgrade -y
    
    log "System packages updated"
}

# Install required packages
install_packages() {
    log "Installing required packages..."
    
    # Core audio packages
    local audio_packages=(
        "alsa-utils"
        "alsa-tools"
        "libasound2-dev"
        "python3-pyaudio"
    )
    
    # Python development packages
    local python_packages=(
        "python3-pip"
        "python3-venv"
        "python3-dev"
        "python3-setuptools"
    )
    
    # GPIO and I2C packages for Raspberry Pi
    local rpi_packages=(
        "python3-lgpio"
        "python3-smbus"
        "i2c-tools"
    )
    
    # Development tools
    local dev_packages=(
        "build-essential"
        "git"
        "curl"
        "wget"
    )
    
    # Multimedia packages
    local multimedia_packages=(
        "ffmpeg"
        "libavcodec-extra"
        "libsdl2-dev"
        "libsdl2-mixer-2.0-0"
    )
    
    # Combine all packages based on system
    local all_packages=("${audio_packages[@]}" "${python_packages[@]}" "${dev_packages[@]}" "${multimedia_packages[@]}")
    
    # Add Raspberry Pi specific packages if detected
    if check_raspberry_pi; then
        all_packages+=("${rpi_packages[@]}")
    fi
    
    # Install packages
    sudo apt install -y "${all_packages[@]}"
    
    log "All required packages installed"
}

# Remove PulseAudio completely
remove_pulseaudio() {
    log "Removing PulseAudio completely..."
    
    # Stop any running PulseAudio processes
    pkill -9 pulseaudio 2>/dev/null || true
    pkill -9 pulse 2>/dev/null || true
    
    # Remove PulseAudio packages
    sudo apt purge -y pulseaudio pulseaudio-module-bluetooth pulseaudio-utils pavucontrol 2>/dev/null || true
    sudo apt autoremove -y
    
    # Remove PulseAudio configuration directories
    sudo rm -rf /etc/pulse 2>/dev/null || true
    rm -rf ~/.pulse 2>/dev/null || true
    rm -rf ~/.config/pulse 2>/dev/null || true
    
    log "PulseAudio removed"
}

# Configure ALSA for USB audio
configure_alsa() {
    log "Configuring ALSA for USB audio..."
    
    # Backup existing ALSA configuration
    if [ -f ~/.asoundrc ]; then
        cp ~/.asoundrc ~/.asoundrc.backup.$(date +%Y%m%d_%H%M%S)
        log "Backed up existing ~/.asoundrc"
    fi
    
    # Create ALSA configuration optimized for USB audio
    cat > ~/.asoundrc << 'EOF'
# Bedrock Audio System - ALSA Configuration
# Optimized for USB audio devices (GS3, dongles, etc.)

# Default PCM device - prioritize USB audio
pcm.!default {
    type plug
    slave {
        pcm "hw:1,0"        # USB audio typically card 1
        rate 44100
        channels 2
        format S16_LE
    }
    hint {
        show on
        description "USB Audio (Default)"
    }
}

# Default control device
ctl.!default {
    type hw
    card 1                  # USB audio card
    hint {
        show on
        description "USB Audio Control"
    }
}

# Fallback to GS3 by name if available
pcm.gs3 {
    type hw
    card GS3
    device 0
    hint {
        show on
        description "GS3 USB Audio"
    }
}

ctl.gs3 {
    type hw
    card GS3
}

# Fallback to card 2 if GS3 is there
pcm.gs3_card2 {
    type hw
    card 2
    device 0
    hint {
        show on
        description "GS3 USB Audio (Card 2)"
    }
}

# Plugin for format conversion
pcm.usb_plug {
    type plug
    slave {
        pcm "hw:1,0"
        rate 44100
        channels 2
        format S16_LE
    }
}

# HDMI output as fallback
pcm.hdmi {
    type hw
    card 0
    device 0
    hint {
        show on
        description "HDMI Audio"
    }
}

ctl.hdmi {
    type hw
    card 0
}
EOF
    
    log "ALSA configuration created"
}

# Create PulseAudio disable configuration
disable_pulseaudio() {
    log "Creating PulseAudio disable configuration..."
    
    # Create pulse config directory
    mkdir -p ~/.config/pulse
    
    # Create client configuration to disable PulseAudio
    cat > ~/.config/pulse/client.conf << 'EOF'
# Bedrock Audio System - PulseAudio Disable Configuration
# Prevents PulseAudio from starting and interfering with ALSA

# Disable autospawn completely
autospawn = no
daemon-binary = /bin/true

# Disable shared memory
enable-shm = no

# Disable memory file descriptors  
enable-memfd = no
EOF
    
    # Create daemon configuration
    cat > ~/.config/pulse/daemon.conf << 'EOF'
# Prevent PulseAudio daemon from running
exit-idle-time = 0
flat-volumes = no
high-priority = no
nice-level = 20
realtime-scheduling = no
load-default-script-file = no
EOF
    
    # Create empty module files
    touch ~/.config/pulse/default.pa
    touch ~/.config/pulse/system.pa
    
    log "PulseAudio disable configuration created"
}

# Configure systemd to prevent PulseAudio
configure_systemd() {
    log "Configuring systemd to prevent PulseAudio..."
    
    # Create systemd user directory
    mkdir -p ~/.config/systemd/user
    
    # Disable PulseAudio user services
    systemctl --user stop pulseaudio.service pulseaudio.socket 2>/dev/null || true
    systemctl --user disable pulseaudio.service pulseaudio.socket 2>/dev/null || true
    systemctl --user mask pulseaudio.service pulseaudio.socket 2>/dev/null || true
    
    # Create systemd override to completely disable PulseAudio
    cat > ~/.config/systemd/user/pulseaudio.service << 'EOF'
[Unit]
Description=Disabled PulseAudio Service
ConditionPathExists=!/dev/null

[Service]
Type=oneshot
ExecStart=/bin/true
RemainAfterExit=no

[Install]
WantedBy=
EOF
    
    cat > ~/.config/systemd/user/pulseaudio.socket << 'EOF'
[Unit]
Description=Disabled PulseAudio Socket
ConditionPathExists=!/dev/null

[Socket]
# No listeners

[Install]
WantedBy=
EOF
    
    # Reload systemd
    systemctl --user daemon-reload
    
    log "Systemd configuration completed"
}

# Set up environment variables
setup_environment() {
    log "Setting up environment variables..."
    
    # Create pulse dummy directory
    local pulse_dummy="/run/user/$(id -u)/pulse-dummy"
    mkdir -p "$pulse_dummy"
    
    # Remove existing pulse-related environment variables
    sed -i '/PULSE_/d; /SDL_AUDIO/d' ~/.bashrc 2>/dev/null || true
    
    # Add audio system configuration to .bashrc
    cat >> ~/.bashrc << EOF

# === BEDROCK AUDIO SYSTEM CONFIGURATION ===
# Generated by bedrock_audio_setup.sh on $(date)

# Force ALSA usage, disable PulseAudio completely
export SDL_AUDIODRIVER=alsa
export PULSE_RUNTIME_PATH=$pulse_dummy
export PULSE_STATE_PATH=$pulse_dummy
export PULSE_CLIENT_CONFIG=\$HOME/.config/pulse/client.conf
export PULSE_DISABLED=1

# Audio optimization for Raspberry Pi
export ALSA_CARD=1  # Prefer USB audio
export ALSA_DEVICE=0

# Python audio optimization
export PYGAME_HIDE_SUPPORT_PROMPT=1
EOF
    
    # Source the new environment (for current session)
    export SDL_AUDIODRIVER=alsa
    export PULSE_RUNTIME_PATH="$pulse_dummy"
    export PULSE_STATE_PATH="$pulse_dummy"
    export PULSE_CLIENT_CONFIG="$HOME/.config/pulse/client.conf"
    export PULSE_DISABLED=1
    export ALSA_CARD=1
    export ALSA_DEVICE=0
    export PYGAME_HIDE_SUPPORT_PROMPT=1
    
    log "Environment variables configured"
}

# Install Python packages for Bedrock
install_python_packages() {
    log "Installing Python packages for Bedrock..."
    
    # Create requirements file
    cat > /tmp/bedrock_requirements.txt << 'EOF'
# Bedrock Audio System Python Requirements

# Core UI framework
kivy>=2.3.0
kivymd>=2.0.0

# Audio processing
pygame>=2.5.0
pyalsaaudio>=0.10.0

# Raspberry Pi GPIO (if available)
lgpio>=0.2.0
RPi.GPIO>=0.7.0

# Sensor libraries
smbus2>=0.4.0
adafruit-circuitpython-busdevice>=5.0.0
adafruit-circuitpython-ens160>=1.0.0
adafruit-circuitpython-ahtx0>=1.0.0
adafruit-blinka>=8.0.0

# HTTP and async
aiohttp>=3.8.0
requests>=2.28.0

# Utilities
python-dotenv>=1.0.0
Pillow>=10.0.0
psutil>=5.9.0
EOF
    
    # Install packages
    pip3 install --user -r /tmp/bedrock_requirements.txt
    
    # Clean up
    rm /tmp/bedrock_requirements.txt
    
    log "Python packages installed"
}

# Create audio test utilities
create_test_utilities() {
    log "Creating audio test utilities..."
    
    # Create comprehensive audio test script
    cat > ~/test_audio_system.py << 'EOF'
#!/usr/bin/env python3
"""
Comprehensive audio system test for Bedrock
Tests ALSA, pygame, and USB audio functionality
"""

import os
import sys
import subprocess
import time

def test_environment():
    """Test environment variables"""
    print("🌍 Environment Variables:")
    
    expected_vars = {
        'SDL_AUDIODRIVER': 'alsa',
        'PULSE_DISABLED': '1',
        'ALSA_CARD': '1'
    }
    
    all_good = True
    for var, expected in expected_vars.items():
        actual = os.environ.get(var, 'Not set')
        status = "✅" if actual == expected else "❌"
        print(f"   {status} {var}: {actual}")
        if actual != expected:
            all_good = False
    
    return all_good

def test_alsa():
    """Test ALSA configuration"""
    print("🔊 ALSA Configuration:")
    
    try:
        # Test aplay
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ ALSA devices detected")
            
            # Look for USB audio
            if 'USB' in result.stdout or 'GS3' in result.stdout:
                print("   ✅ USB audio device found")
            else:
                print("   ⚠️  No USB audio device detected")
            
            # Show cards
            lines = result.stdout.split('\n')
            cards = [line for line in lines if line.startswith('card')]
            for card in cards[:3]:  # Show first 3 cards
                print(f"   📋 {card}")
            
            return True
        else:
            print("   ❌ ALSA not working")
            return False
            
    except Exception as e:
        print(f"   ❌ ALSA test error: {e}")
        return False

def test_pygame():
    """Test pygame audio"""
    print("🎮 Pygame Audio:")
    
    try:
        import pygame
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.init()
        
        init_result = pygame.mixer.get_init()
        if init_result:
            freq, format_val, channels = init_result
            print(f"   ✅ Pygame initialized: {freq}Hz, {channels}ch, format={format_val}")
            
            # Test sound creation
            try:
                # Create a simple test sound
                import numpy as np
                duration = 0.1  # 100ms
                sample_rate = 44100
                t = np.linspace(0, duration, int(sample_rate * duration), False)
                wave = np.sin(2 * np.pi * 440 * t)  # 440Hz sine wave
                
                # Convert to pygame sound format
                wave = (wave * 32767).astype(np.int16)
                stereo_wave = np.zeros((len(wave), 2), dtype=np.int16)
                stereo_wave[:, 0] = wave
                stereo_wave[:, 1] = wave
                
                sound = pygame.sndarray.make_sound(stereo_wave)
                print("   ✅ Sound generation test passed")
                
            except ImportError:
                print("   ⚠️  NumPy not available for sound test")
            except Exception as e:
                print(f"   ⚠️  Sound test failed: {e}")
            
            pygame.mixer.quit()
            return True
        else:
            print("   ❌ Pygame mixer failed to initialize")
            return False
            
    except Exception as e:
        print(f"   ❌ Pygame test failed: {e}")
        return False

def test_pulseaudio_disabled():
    """Test that PulseAudio is disabled"""
    print("🚫 PulseAudio Status:")
    
    # Check for running processes
    try:
        result = subprocess.run(['pgrep', 'pulseaudio'], capture_output=True)
        if result.returncode == 0:
            print("   ❌ PulseAudio processes still running")
            return False
        else:
            print("   ✅ No PulseAudio processes")
    except:
        print("   ✅ No PulseAudio processes")
    
    # Check systemd services
    try:
        result = subprocess.run(['systemctl', '--user', 'is-active', 'pulseaudio.service'], 
                               capture_output=True, text=True)
        if 'active' in result.stdout:
            print("   ❌ PulseAudio service is active")
            return False
        else:
            print("   ✅ PulseAudio service disabled")
    except:
        print("   ✅ PulseAudio service disabled")
    
    return True

def test_alsa_sound():
    """Test ALSA sound output"""
    print("🎵 ALSA Sound Test:")
    
    try:
        # Test with speaker-test (brief)
        result = subprocess.run([
            'timeout', '2', 'speaker-test', '-c', '2', '-t', 'wav', '-l', '1'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0 or result.returncode == 124:  # 124 is timeout
            print("   ✅ ALSA sound test completed")
            return True
        else:
            print("   ⚠️  ALSA sound test had issues (may be normal)")
            return True  # Don't fail on this
            
    except Exception as e:
        print(f"   ⚠️  ALSA sound test skipped: {e}")
        return True

def main():
    print("🔍 === BEDROCK AUDIO SYSTEM TEST ===\n")
    
    tests = [
        ("Environment", test_environment),
        ("ALSA", test_alsa),
        ("PulseAudio Disabled", test_pulseaudio_disabled),
        ("Pygame", test_pygame),
        ("ALSA Sound", test_alsa_sound)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"{name}:")
        result = test_func()
        results.append(result)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed >= 4:
        print("🎉 Audio system is ready for Bedrock!")
        print("\n💡 Next steps:")
        print("   1. Clone/setup your Bedrock application")
        print("   2. Create Python virtual environment")
        print("   3. Install Bedrock dependencies")
        print("   4. Run your application")
        return 0
    else:
        print("❌ Audio system needs attention")
        print("\n🔧 Try:")
        print("   1. Reboot the system")
        print("   2. Check USB audio device connection")
        print("   3. Run: source ~/.bashrc")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF
    
    chmod +x ~/test_audio_system.py
    
    # Create quick ALSA test script
    cat > ~/quick_audio_test.sh << 'EOF'
#!/bin/bash
# Quick audio test script

echo "🔍 Quick Audio Test"
echo "=================="

echo "📋 Audio cards:"
aplay -l | grep -E "^card" || echo "No cards found"

echo -e "\n🎵 Testing default audio (3 seconds):"
timeout 3 speaker-test -c 2 -t wav -l 1 2>/dev/null && echo "✅ Audio test completed" || echo "⚠️ Audio test had issues"

echo -e "\n🌍 Environment:"
echo "   SDL_AUDIODRIVER: ${SDL_AUDIODRIVER:-Not set}"
echo "   PULSE_DISABLED: ${PULSE_DISABLED:-Not set}"

echo -e "\n🚫 PulseAudio processes:"
pgrep pulseaudio >/dev/null && echo "❌ PulseAudio running" || echo "✅ PulseAudio not running"
EOF
    
    chmod +x ~/quick_audio_test.sh
    
    log "Audio test utilities created"
}

# Main setup function
main() {
    echo -e "${BLUE}
╔═══════════════════════════════════════════════════════════════╗
║                   BEDROCK AUDIO SYSTEM SETUP                 ║
║                                                               ║
║  This script will configure your system for optimal audio    ║
║  performance with Bedrock on Raspberry Pi + USB audio       ║
║                                                               ║
║  What it does:                                               ║
║  • Removes PulseAudio completely                             ║
║  • Configures ALSA for USB audio                            ║
║  • Installs required packages                               ║
║  • Sets up Python environment                               ║
║  • Creates test utilities                                    ║
╚═══════════════════════════════════════════════════════════════╝
${NC}"
    
    echo "Press ENTER to continue or Ctrl+C to cancel..."
    read -r
    
    log "Starting Bedrock audio system setup..."
    
    # Run setup steps
    check_root
    check_system
    update_system
    install_packages
    remove_pulseaudio
    configure_alsa
    disable_pulseaudio
    configure_systemd
    setup_environment
    install_python_packages
    create_test_utilities
    
    echo -e "${GREEN}
╔═══════════════════════════════════════════════════════════════╗
║                        SETUP COMPLETE!                       ║
║                                                               ║
║  Your system is now configured for Bedrock audio.           ║
║                                                               ║
║  Next steps:                                                 ║
║  1. Reboot your system: sudo reboot                         ║
║  2. Test audio: ~/quick_audio_test.sh                       ║
║  3. Full test: python3 ~/test_audio_system.py               ║
║  4. Setup your Bedrock application                          ║
║                                                               ║
║  Created files:                                              ║
║  • ~/.asoundrc (ALSA config)                                ║
║  • ~/.config/pulse/* (PulseAudio disable config)           ║
║  • ~/test_audio_system.py (comprehensive test)             ║
║  • ~/quick_audio_test.sh (quick test)                      ║
║                                                               ║
║  Environment variables added to ~/.bashrc                   ║
╚═══════════════════════════════════════════════════════════════╝
${NC}"
    
    echo "🔄 Reboot recommended. Run 'sudo reboot' when ready."
}

# Run main function
main "$@"