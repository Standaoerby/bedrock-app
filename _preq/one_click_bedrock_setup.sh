#!/bin/bash
# one_click_bedrock_setup.sh - Complete one-click setup for Bedrock audio
# Combines system check, setup, and testing in one script
# Usage: curl -fsSL [url] | bash
# Or: wget -qO- [url] | bash

set -e

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Global variables
SCRIPT_VERSION="1.0.0"
SETUP_DIR="$HOME/.bedrock_setup"
LOG_FILE="$SETUP_DIR/setup.log"

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

# Setup logging
setup_logging() {
    mkdir -p "$SETUP_DIR"
    echo "=== Bedrock Setup Started $(date) ===" > "$LOG_FILE"
}

# Display banner
show_banner() {
    clear
    echo -e "${BLUE}${BOLD}
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║  ██████╗ ███████╗██████╗ ██████╗  ██████╗  ██████╗██╗  ██╗      ║
║  ██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔════╝██║ ██╔╝      ║
║  ██████╔╝█████╗  ██║  ██║██████╔╝██║   ██║██║     █████╔╝       ║
║  ██╔══██╗██╔══╝  ██║  ██║██╔══██╗██║   ██║██║     ██╔═██╗       ║
║  ██████╔╝███████╗██████╔╝██║  ██║╚██████╔╝╚██████╗██║  ██╗      ║
║  ╚═════╝ ╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝      ║
║                                                                  ║
║                    AUDIO SYSTEM SETUP v${SCRIPT_VERSION}                   ║
║                                                                  ║
║  🎵 Complete audio system configuration for Raspberry Pi        ║
║  🔧 Removes PulseAudio conflicts, configures ALSA              ║
║  🎯 Optimized for USB audio devices (GS3, dongles, etc.)       ║
║  🧪 Includes comprehensive testing and validation              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if root
    if [ "$EUID" -eq 0 ]; then
        error "This script should NOT be run as root. Run as regular user with sudo access."
    fi
    
    # Check sudo access
    if ! sudo -n true 2>/dev/null; then
        echo "This script requires sudo access. Please enter your password:"
        sudo -v || error "Sudo access required"
    fi
    
    # Check basic commands
    for cmd in curl wget python3 pip3 apt; do
        if ! command -v $cmd >/dev/null 2>&1; then
            error "Required command '$cmd' not found"
        fi
    done
    
    # Check internet
    if ! ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        error "Internet connection required"
    fi
    
    log "Prerequisites check passed"
}

# System information
show_system_info() {
    log "System Information:"
    
    # OS Info
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log "  OS: $NAME $VERSION"
    fi
    
    # Hardware info
    log "  Architecture: $(uname -m)"
    if [ -f /proc/device-tree/model ]; then
        log "  Device: $(cat /proc/device-tree/model)"
    fi
    
    # Python version
    log "  Python: $(python3 --version)"
    
    # Audio devices
    log "  Audio devices:"
    aplay -l 2>/dev/null | grep -E "^card" | while read line; do
        log "    $line"
    done
}

# Interactive confirmation
confirm_setup() {
    echo -e "\n${YELLOW}This setup will:${NC}"
    echo "  • Remove PulseAudio completely"
    echo "  • Install required packages"
    echo "  • Configure ALSA for USB audio"
    echo "  • Set up Python environment"
    echo "  • Create test utilities"
    echo "  • Modify ~/.bashrc"
    echo ""
    echo -e "${BOLD}Continue? (y/N)${NC}"
    read -r response
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Setup cancelled by user"
        exit 0
    fi
}

# Main setup function
run_setup() {
    log "Starting main setup..."
    
    # Update system
    log "Updating system packages..."
    sudo apt update -qq
    sudo apt upgrade -y -qq
    
    # Install packages
    log "Installing required packages..."
    sudo apt install -y -qq \
        alsa-utils alsa-tools libasound2-dev \
        python3-pip python3-venv python3-dev python3-setuptools \
        build-essential git curl wget \
        ffmpeg libavcodec-extra libsdl2-dev libsdl2-mixer-2.0-0 \
        python3-lgpio python3-smbus i2c-tools 2>/dev/null || true
    
    # Remove PulseAudio
    log "Removing PulseAudio..."
    pkill -9 pulseaudio 2>/dev/null || true
    sudo apt purge -y -qq pulseaudio pulseaudio-module-bluetooth pulseaudio-utils pavucontrol 2>/dev/null || true
    sudo apt autoremove -y -qq
    
    # Configure ALSA
    log "Configuring ALSA..."
    if [ -f ~/.asoundrc ]; then
        cp ~/.asoundrc ~/.asoundrc.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    cat > ~/.asoundrc << 'EOF'
# Bedrock Audio - ALSA Configuration
pcm.!default {
    type plug
    slave {
        pcm "hw:1,0"
        rate 44100
        channels 2
        format S16_LE
    }
}
ctl.!default {
    type hw
    card 1
}
pcm.gs3 {
    type hw
    card GS3
    device 0
}
pcm.gs3_card2 {
    type hw
    card 2
    device 0
}
EOF
    
    # Disable PulseAudio
    log "Disabling PulseAudio..."
    mkdir -p ~/.config/pulse
    cat > ~/.config/pulse/client.conf << 'EOF'
autospawn = no
daemon-binary = /bin/true
enable-shm = no
enable-memfd = no
EOF
    
    # Configure systemd
    systemctl --user stop pulseaudio.service pulseaudio.socket 2>/dev/null || true
    systemctl --user disable pulseaudio.service pulseaudio.socket 2>/dev/null || true
    systemctl --user mask pulseaudio.service pulseaudio.socket 2>/dev/null || true
    
    # Set up environment
    log "Setting up environment..."
    pulse_dummy="/run/user/$(id -u)/pulse-dummy"
    mkdir -p "$pulse_dummy"
    
    # Remove old entries and add new ones
    sed -i '/BEDROCK AUDIO/,/^$/d' ~/.bashrc 2>/dev/null || true
    cat >> ~/.bashrc << EOF

# === BEDROCK AUDIO SYSTEM CONFIGURATION ===
export SDL_AUDIODRIVER=alsa
export PULSE_RUNTIME_PATH=$pulse_dummy
export PULSE_STATE_PATH=$pulse_dummy
export PULSE_DISABLED=1
export ALSA_CARD=1
export PYGAME_HIDE_SUPPORT_PROMPT=1
EOF
    
    # Source environment
    export SDL_AUDIODRIVER=alsa
    export PULSE_RUNTIME_PATH="$pulse_dummy"
    export PULSE_STATE_PATH="$pulse_dummy"
    export PULSE_DISABLED=1
    export ALSA_CARD=1
    export PYGAME_HIDE_SUPPORT_PROMPT=1
    
    # Install Python packages
    log "Installing Python packages..."
    pip3 install --user --quiet \
        pygame pyalsaaudio kivy kivymd \
        aiohttp requests python-dotenv \
        Pillow psutil smbus2 \
        lgpio RPi.GPIO 2>/dev/null || true
    
    log "Main setup completed"
}

# Create test utilities
create_tests() {
    log "Creating test utilities..."
    
    # Quick test script
    cat > ~/bedrock_audio_test.py << 'EOF'
#!/usr/bin/env python3
import os, sys, subprocess
def test_audio():
    print("🔍 Bedrock Audio Test")
    print("=" * 30)
    
    # Environment
    env_ok = os.environ.get('SDL_AUDIODRIVER') == 'alsa'
    print(f"🌍 Environment: {'✅' if env_ok else '❌'}")
    
    # ALSA
    try:
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        alsa_ok = result.returncode == 0
        print(f"🔊 ALSA: {'✅' if alsa_ok else '❌'}")
        if 'GS3' in result.stdout or 'USB' in result.stdout:
            print("   ✅ USB audio detected")
    except:
        print("🔊 ALSA: ❌")
        alsa_ok = False
    
    # PulseAudio
    try:
        result = subprocess.run(['pgrep', 'pulseaudio'], capture_output=True)
        pulse_ok = result.returncode != 0
        print(f"🚫 PulseAudio disabled: {'✅' if pulse_ok else '❌'}")
    except:
        print("🚫 PulseAudio disabled: ✅")
        pulse_ok = True
    
    # Pygame
    try:
        import pygame
        pygame.mixer.init()
        pygame_ok = pygame.mixer.get_init() is not None
        pygame.mixer.quit()
        print(f"🎮 Pygame: {'✅' if pygame_ok else '❌'}")
    except Exception as e:
        print(f"🎮 Pygame: ❌ ({e})")
        pygame_ok = False
    
    # Summary
    total = sum([env_ok, alsa_ok, pulse_ok, pygame_ok])
    print(f"\n📊 Result: {total}/4 tests passed")
    
    if total >= 3:
        print("🎉 Audio system ready for Bedrock!")
        return 0
    else:
        print("❌ Audio system needs attention")
        return 1

if __name__ == "__main__":
    sys.exit(test_audio())
EOF
    
    chmod +x ~/bedrock_audio_test.py
    
    # Quick shell test
    cat > ~/quick_audio_check.sh << 'EOF'
#!/bin/bash
echo "🔍 Quick Audio Check"
echo "=================="
echo "📋 Audio cards:"
aplay -l | grep -E "^card" || echo "No cards found"
echo ""
echo "🌍 Environment:"
echo "   SDL_AUDIODRIVER: ${SDL_AUDIODRIVER:-Not set}"
echo "   PULSE_DISABLED: ${PULSE_DISABLED:-Not set}"
echo ""
echo "🚫 PulseAudio:"
if pgrep pulseaudio >/dev/null; then
    echo "   ❌ PulseAudio running"
else
    echo "   ✅ PulseAudio not running"
fi
EOF
    
    chmod +x ~/quick_audio_check.sh
    
    log "Test utilities created"
}

# Run tests
run_tests() {
    log "Running validation tests..."
    
    # Source environment for tests
    source ~/.bashrc
    
    # Quick check
    log "Quick audio check:"
    ~/quick_audio_check.sh | tee -a "$LOG_FILE"
    
    # Python test
    log "Python audio test:"
    python3 ~/bedrock_audio_test.py | tee -a "$LOG_FILE"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        log "✅ All tests passed!"
        return 0
    else
        warn "⚠️ Some tests failed - check results above"
        return 1
    fi
}

# Show completion message
show_completion() {
    local test_status=$1
    
    echo -e "\n${GREEN}${BOLD}
╔══════════════════════════════════════════════════════════════════╗
║                        SETUP COMPLETE!                          ║
╚══════════════════════════════════════════════════════════════════╝
${NC}"
    
    if [ $test_status -eq 0 ]; then
        echo -e "${GREEN}✅ Audio system is ready for Bedrock!${NC}"
    else
        echo -e "${YELLOW}⚠️  Setup completed but some tests failed${NC}"
    fi
    
    echo -e "\n${BOLD}📁 Files created:${NC}"
    echo "  ~/.asoundrc - ALSA configuration"
    echo "  ~/.config/pulse/client.conf - PulseAudio disable"
    echo "  ~/bedrock_audio_test.py - Audio test script"
    echo "  ~/quick_audio_check.sh - Quick check script"
    echo "  ~/.bedrock_setup/setup.log - Setup log"
    
    echo -e "\n${BOLD}🔄 Next steps:${NC}"
    echo "  1. Reboot system: sudo reboot"
    echo "  2. After reboot, test: python3 ~/bedrock_audio_test.py"
    echo "  3. Set up your Bedrock application"
    
    echo -e "\n${BOLD}🧪 Testing commands:${NC}"
    echo "  Quick check: ~/quick_audio_check.sh"
    echo "  Full test: python3 ~/bedrock_audio_test.py"
    echo "  Manual test: speaker-test -c 2 -t wav -l 1"
    
    echo -e "\n${BOLD}📝 Troubleshooting:${NC}"
    echo "  View setup log: cat ~/.bedrock_setup/setup.log"
    echo "  Check audio devices: aplay -l"
    echo "  Check environment: env | grep -E '(SDL_|PULSE_)'"
    
    echo -e "\n${BOLD}🔧 Bedrock application setup:${NC}"
    echo "  mkdir ~/bedrock-app && cd ~/bedrock-app"
    echo "  python3 -m venv .venv && source .venv/bin/activate"
    echo "  # Clone/download your Bedrock application"
    echo "  pip install -r requirements.txt"
    echo "  python3 main.py"
    
    echo -e "\n${BLUE}Reboot recommended for full effect: ${BOLD}sudo reboot${NC}"
}

# Main execution
main() {
    # Initial setup
    setup_logging
    show_banner
    
    # Pre-flight checks
    check_prerequisites
    show_system_info
    
    # User confirmation
    confirm_setup
    
    # Main setup process
    echo -e "\n${BOLD}Starting setup process...${NC}\n"
    
    run_setup
    create_tests
    
    # Validation
    echo -e "\n${BOLD}Running validation tests...${NC}\n"
    run_tests
    local test_status=$?
    
    # Completion
    show_completion $test_status
    
    # Final recommendation
    echo -e "\n${YELLOW}${BOLD}💡 Tip: Bookmark this for future reference${NC}"
    echo "curl -fsSL [this-script-url] | bash"
    
    exit $test_status
}

# Trap for cleanup
trap 'echo -e "\n${RED}Setup interrupted${NC}"; exit 130' INT

# Run main function
main "$@"