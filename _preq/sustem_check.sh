#!/bin/bash
# system_check.sh - Pre-setup system requirements check
# Run this before bedrock_audio_setup.sh to verify system compatibility

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check functions
check_os() {
    echo "🐧 Operating System:"
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "   OS: $NAME $VERSION"
        
        # Check if Debian-based
        if [[ "$ID" == "debian" ]] || [[ "$ID_LIKE" == *"debian"* ]] || [[ "$ID" == "raspbian" ]]; then
            echo "   ✅ Debian-based OS detected"
            return 0
        else
            echo "   ⚠️  Non-Debian OS - script may need modifications"
            return 1
        fi
    else
        echo "   ❌ Cannot detect OS"
        return 1
    fi
}

check_hardware() {
    echo "🔧 Hardware:"
    
    # Check if Raspberry Pi
    if [ -f /proc/device-tree/model ]; then
        local model=$(cat /proc/device-tree/model 2>/dev/null)
        echo "   Device: $model"
        
        if [[ "$model" == *"Raspberry Pi"* ]]; then
            echo "   ✅ Raspberry Pi detected"
            
            # Check Pi version
            if [[ "$model" == *"Pi 5"* ]]; then
                echo "   ✅ Raspberry Pi 5 - excellent for Bedrock"
            elif [[ "$model" == *"Pi 4"* ]]; then
                echo "   ✅ Raspberry Pi 4 - good for Bedrock"
            else
                echo "   ⚠️  Older Pi model - may have performance limitations"
            fi
        fi
    else
        echo "   ℹ️  Not a Raspberry Pi - generic Linux setup will be used"
    fi
    
    # Check architecture
    local arch=$(uname -m)
    echo "   Architecture: $arch"
    
    if [[ "$arch" == "aarch64" ]] || [[ "$arch" == "armv7l" ]]; then
        echo "   ✅ ARM architecture - suitable for Pi"
    else
        echo "   ℹ️  x86/x64 architecture - generic Linux setup"
    fi
}

check_python() {
    echo "🐍 Python:"
    
    if command -v python3 >/dev/null 2>&1; then
        local version=$(python3 --version | cut -d' ' -f2)
        echo "   Version: $version"
        
        # Check if version is 3.8+
        local major=$(echo $version | cut -d'.' -f1)
        local minor=$(echo $version | cut -d'.' -f2)
        
        if [ "$major" -eq 3 ] && [ "$minor" -ge 8 ]; then
            echo "   ✅ Python 3.8+ available"
        else
            echo "   ⚠️  Python 3.8+ recommended for Kivy"
        fi
    else
        echo "   ❌ Python 3 not found"
        return 1
    fi
    
    # Check pip
    if command -v pip3 >/dev/null 2>&1; then
        echo "   ✅ pip3 available"
    else
        echo "   ⚠️  pip3 not found - will be installed"
    fi
}

check_audio() {
    echo "🔊 Audio System:"
    
    # Check ALSA
    if command -v aplay >/dev/null 2>&1; then
        echo "   ✅ ALSA tools available"
        
        # List audio devices
        local cards=$(aplay -l 2>/dev/null | grep -c "^card")
        echo "   Audio cards detected: $cards"
        
        # Check for USB audio
        if aplay -l 2>/dev/null | grep -i "usb\|gs3" >/dev/null; then
            echo "   ✅ USB audio device detected"
        else
            echo "   ⚠️  No USB audio detected (connect USB audio device)"
        fi
        
    else
        echo "   ⚠️  ALSA tools not installed - will be installed"
    fi
    
    # Check PulseAudio status
    if command -v pulseaudio >/dev/null 2>&1; then
        echo "   ⚠️  PulseAudio detected - will be removed"
        
        if pgrep pulseaudio >/dev/null; then
            echo "   ⚠️  PulseAudio is running - will be stopped"
        fi
    else
        echo "   ✅ PulseAudio not installed"
    fi
}

check_permissions() {
    echo "👤 Permissions:"
    
    # Check if user is in audio group
    if groups | grep -q audio; then
        echo "   ✅ User in audio group"
    else
        echo "   ⚠️  User not in audio group - will be added"
    fi
    
    # Check sudo access
    if sudo -n true 2>/dev/null; then
        echo "   ✅ Sudo access available"
    else
        echo "   ⚠️  Sudo access required for setup"
    fi
}

check_storage() {
    echo "💾 Storage:"
    
    # Check available space
    local available=$(df -h . | awk 'NR==2 {print $4}')
    local available_mb=$(df -m . | awk 'NR==2 {print $4}')
    
    echo "   Available space: $available"
    
    if [ "$available_mb" -gt 1000 ]; then
        echo "   ✅ Sufficient storage space"
    else
        echo "   ⚠️  Low storage space - recommend 1GB+ free"
    fi
}

check_network() {
    echo "🌐 Network:"
    
    # Check internet connectivity
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        echo "   ✅ Internet connectivity available"
    else
        echo "   ❌ No internet connection - required for package installation"
        return 1
    fi
    
    # Check package repositories
    if timeout 5 apt update -qq 2>/dev/null; then
        echo "   ✅ Package repositories accessible"
    else
        echo "   ⚠️  Package repositories may be slow"
    fi
}

main() {
    echo -e "${BLUE}
╔══════════════════════════════════════════════════════╗
║              BEDROCK SYSTEM REQUIREMENTS CHECK      ║
║                                                      ║
║  This script checks if your system is ready for     ║
║  Bedrock audio system setup.                        ║
╚══════════════════════════════════════════════════════╝
${NC}"
    
    echo "🔍 Checking system requirements...\n"
    
    # Run all checks
    local checks=(
        "check_os"
        "check_hardware" 
        "check_python"
        "check_audio"
        "check_permissions"
        "check_storage"
        "check_network"
    )
    
    local results=()
    
    for check in "${checks[@]}"; do
        $check
        results+=($?)
        echo
    done
    
    # Analyze results
    local failed=0
    for result in "${results[@]}"; do
        if [ "$result" -ne 0 ]; then
            ((failed++))
        fi
    done
    
    echo "📊 Summary:"
    echo "   Total checks: ${#checks[@]}"
    echo "   Failed: $failed"
    echo "   Passed: $((${#checks[@]} - failed))"
    
    if [ "$failed" -eq 0 ]; then
        echo -e "\n${GREEN}✅ Your system is ready for Bedrock setup!${NC}"
        echo -e "Run: ${YELLOW}./bedrock_audio_setup.sh${NC}"
        return 0
    elif [ "$failed" -le 2 ]; then
        echo -e "\n${YELLOW}⚠️  Your system has minor issues but setup should work.${NC}"
        echo -e "Run: ${YELLOW}./bedrock_audio_setup.sh${NC}"
        return 0
    else
        echo -e "\n${RED}❌ Your system has significant issues.${NC}"
        echo "Please address the failed checks before running setup."
        return 1
    fi
}

main "$@"