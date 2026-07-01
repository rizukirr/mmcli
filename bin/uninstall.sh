#!/bin/bash
# Complete Uninstallation Script for mmcli YouTube downloader (Linux/Mac)
# This script removes mmcli that was installed globally using pipx

set -e

echo "=== MMCLI Uninstallation Script ==="
echo "This will remove mmcli that was installed globally using pipx"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

print_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

print_info() {
    echo -e "${YELLOW}INFO:${NC} $1"
}

# Step 1: Check if pipx is available
echo "Step 1: Checking pipx installation..."
if ! command -v pipx &> /dev/null; then
    # Check if Python is available to use pipx module
    if ! command -v python3 &> /dev/null; then
        if ! command -v python &> /dev/null; then
            print_error "Python not found! Cannot proceed with uninstallation."
            echo "pipx might not be available to uninstall mmcli"
            exit 1
        else
            PYTHON_CMD="python"
        fi
    else
        PYTHON_CMD="python3"
    fi
    
    # Check if pipx module is available
    if ! $PYTHON_CMD -m pipx --version &> /dev/null; then
        print_error "pipx not found! mmcli might not have been installed via pipx."
        echo "If mmcli was installed differently, please remove it manually."
        exit 1
    fi
    
    print_warning "pipx command not found, using Python module"
    PIPX_CMD="$PYTHON_CMD -m pipx"
else
    print_success "pipx is available"
    PIPX_CMD="pipx"
fi

echo

# Step 2: Check if mmcli is currently installed
echo "Step 2: Checking if mmcli is installed..."
if ! $PIPX_CMD list | grep -q "mmcli"; then
    print_warning "mmcli not found in pipx installations"
    
    # Check if mmcli command is still available
    if command -v mmcli &> /dev/null; then
        print_warning "mmcli command found but not in pipx list"
        echo "mmcli might have been installed via a different method"
        echo
        read -p "Continue anyway to attempt removal? (y/n): " continue_removal
        if [[ ! $continue_removal =~ ^[Yy]$ ]]; then
            exit 0
        fi
    else
        print_info "mmcli is not currently installed"
        exit 0
    fi
else
    print_success "mmcli found in pipx installations"
fi

echo

# Step 3: Uninstall mmcli
echo "Step 3: Uninstalling mmcli..."
if ! $PIPX_CMD uninstall mmcli; then
    print_error "Failed to uninstall mmcli with $PIPX_CMD!"
    echo "Trying alternative method..."
    if [[ "$PIPX_CMD" != "$PYTHON_CMD -m pipx" ]]; then
        if ! $PYTHON_CMD -m pipx uninstall mmcli; then
            print_error "Uninstallation failed with both methods!"
            exit 1
        fi
    else
        print_error "Uninstallation failed!"
        exit 1
    fi
fi
print_success "mmcli uninstalled successfully"

echo

# Step 4: Verify removal
echo "Step 4: Verifying removal..."
if command -v mmcli &> /dev/null; then
    print_warning "mmcli command is still available"
    echo "This might indicate:"
    echo "  - mmcli was installed in multiple ways"
    echo "  - PATH cache needs to be refreshed"
    echo "  - Different installation method was used"
    echo
    echo "Try restarting your terminal and check again"
else
    print_success "mmcli command is no longer available"
fi

# Step 5: Optional cleanup
echo
echo "Step 5: Optional cleanup..."

# Ask about ffmpeg removal
if command -v ffmpeg &> /dev/null; then
    echo
    read -p "Would you like to remove ffmpeg as well? (y/n): " remove_ffmpeg
    if [[ $remove_ffmpeg =~ ^[Yy]$ ]]; then
        echo "Attempting to remove ffmpeg..."
        
        # Check if we're on macOS and Homebrew is available
        if [[ "$OSTYPE" == "darwin"* ]] && command -v brew &> /dev/null; then
            if brew list ffmpeg &> /dev/null; then
                echo "Removing ffmpeg via Homebrew..."
                if brew uninstall ffmpeg; then
                    print_success "ffmpeg removed successfully via Homebrew"
                else
                    print_error "Failed to remove ffmpeg via Homebrew"
                fi
            else
                print_info "ffmpeg not installed via Homebrew"
            fi
        # Check if we're on Ubuntu/Debian
        elif command -v apt &> /dev/null; then
            echo "Removing ffmpeg via apt..."
            if sudo apt remove -y ffmpeg; then
                print_success "ffmpeg removed successfully via apt"
            else
                print_error "Failed to remove ffmpeg via apt"
            fi
        # Check if we're on CentOS/RHEL
        elif command -v yum &> /dev/null; then
            echo "Removing ffmpeg via yum..."
            if sudo yum remove -y ffmpeg; then
                print_success "ffmpeg removed successfully via yum"
            else
                print_error "Failed to remove ffmpeg via yum"
            fi
        # Check if we're on Fedora
        elif command -v dnf &> /dev/null; then
            echo "Removing ffmpeg via dnf..."
            if sudo dnf remove -y ffmpeg; then
                print_success "ffmpeg removed successfully via dnf"
            else
                print_error "Failed to remove ffmpeg via dnf"
            fi
        # Check if we're on Arch Linux
        elif command -v pacman &> /dev/null; then
            echo "Removing ffmpeg via pacman..."
            if sudo pacman -R --noconfirm ffmpeg; then
                print_success "ffmpeg removed successfully via pacman"
            else
                print_error "Failed to remove ffmpeg via pacman"
            fi
        else
            print_warning "Cannot automatically remove ffmpeg on this system"
            echo "Please remove ffmpeg manually using your system's package manager"
        fi
    fi
else
    print_info "ffmpeg not found in PATH"
fi

echo
read -p "Would you like to remove pipx if it's no longer needed? (y/n): " remove_pipx
if [[ $remove_pipx =~ ^[Yy]$ ]]; then
    # Check if pipx has any other packages
    if $PIPX_CMD list | grep -q "package"; then
        print_info "pipx has other packages installed, keeping pipx"
        $PIPX_CMD list
    else
        echo "Removing pipx..."
        if [[ "$PIPX_CMD" == "pipx" ]]; then
            pip uninstall -y pipx
        else
            $PYTHON_CMD -m pip uninstall -y pipx
        fi
        print_success "pipx removed"
    fi
fi

echo
echo "=== Uninstallation Complete! ==="
echo
print_success "mmcli has been successfully removed from your system!"
echo
echo "If you want to reinstall mmcli later, run:"
echo "  ./bin/install.sh"
echo
echo "Thank you for using mmcli!"
echo