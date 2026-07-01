#!/bin/bash
# Complete Installation Script for mmcli YouTube downloader (Linux/Mac)
# This script installs mmcli globally using pipx

set -e

echo "=== MMCLI Installation Script ==="
echo "This will install mmcli globally using pipx"
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

# Step 1: Check prerequisites
echo "Step 1: Checking system prerequisites..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        print_error "Python not found! Please install Python first."
        echo "Visit: https://python.org/downloads/"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
print_success "$PYTHON_VERSION found"

# Check if pip is available
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    print_error "pip not found! Please ensure pip is installed with Python."
    exit 1
fi
print_success "pip is available"

# Check if ffmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    print_warning "ffmpeg not found in PATH!"
    echo "mmcli requires ffmpeg for media conversion."
    echo
    echo "Installation options:"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg"
    echo "  CentOS/RHEL:   sudo yum install ffmpeg"
    echo "  Fedora:        sudo dnf install ffmpeg"
    echo "  macOS:         brew install ffmpeg"
    echo "  Arch Linux:    sudo pacman -S ffmpeg"
    echo
    
    # Check if we're on macOS and Homebrew is available
    if [[ "$OSTYPE" == "darwin"* ]] && command -v brew &> /dev/null; then
        read -p "Would you like to install ffmpeg via Homebrew? (y/n): " install_ffmpeg
        if [[ $install_ffmpeg =~ ^[Yy]$ ]]; then
            echo "Installing ffmpeg via Homebrew..."
            if brew install ffmpeg; then
                print_success "ffmpeg installed successfully via Homebrew"
            else
                print_error "Failed to install ffmpeg via Homebrew"
                echo "Please install manually"
            fi
        fi
    # Check if we're on Ubuntu/Debian
    elif command -v apt &> /dev/null; then
        read -p "Would you like to install ffmpeg via apt? (y/n): " install_ffmpeg
        if [[ $install_ffmpeg =~ ^[Yy]$ ]]; then
            echo "Installing ffmpeg via apt..."
            if sudo apt update && sudo apt install -y ffmpeg; then
                print_success "ffmpeg installed successfully via apt"
            else
                print_error "Failed to install ffmpeg via apt"
                echo "Please install manually"
            fi
        fi
    fi
    
    echo
    read -p "Continue mmcli installation anyway? (y/n): " continue_install
    if [[ ! $continue_install =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "ffmpeg is available"
fi

echo

# Step 2: Install pipx if not available
echo "Step 2: Checking pipx installation..."
if ! command -v pipx &> /dev/null; then
    echo "pipx not found, installing..."
    $PYTHON_CMD -m pip install --user pipx
    
    # Ensure pipx is in PATH
    $PYTHON_CMD -m pipx ensurepath
    
    print_success "pipx installed successfully"
    print_success "pipx PATH configured"
    echo
    echo "NOTE: If pipx commands still fail, use '$PYTHON_CMD -m pipx' instead of 'pipx'"
    PIPX_CMD="$PYTHON_CMD -m pipx"
else
    print_success "pipx is available"
    PIPX_CMD="pipx"
fi

# Step 3: Navigate to project root
echo "Step 3: Preparing installation..."
cd "$(dirname "$0")/.."
if [[ ! -f "main.py" ]]; then
    print_error "main.py not found! Please run this script from the bin/ directory."
    exit 1
fi
print_success "Project root located"

# Step 4: Install mmcli globally using pipx
echo "Step 4: Installing mmcli globally using pipx..."
if ! $PIPX_CMD install -e .; then
    print_error "Installation failed with $PIPX_CMD!"
    echo "Trying alternative method..."
    if [[ "$PIPX_CMD" != "$PYTHON_CMD -m pipx" ]]; then
        if ! $PYTHON_CMD -m pipx install -e .; then
            print_error "Installation failed with both methods!"
            exit 1
        fi
    else
        print_error "Installation failed! Make sure you have restarted your terminal"
        exit 1
    fi
fi
print_success "mmcli installed successfully"

# Step 6: Verify installation
echo "Step 6: Verifying installation..."
if ! mmcli --version &> /dev/null; then
    echo "Testing with --help instead..."
    if ! mmcli --help &> /dev/null; then
        print_error "mmcli command not found after installation!"
        echo "This might be because pipx's bin directory is not in your PATH."
        echo
        echo "SOLUTIONS:"
        echo "1. Restart your terminal and try again"
        echo "2. Run: $PYTHON_CMD -m pipx ensurepath"
        echo "3. Manually add pipx bin directory to PATH:"
        USER_BASE=$($PYTHON_CMD -c "import site; print(site.USER_BASE)")
        echo "   Add to PATH: $USER_BASE/bin"
        echo
        exit 1
    fi
fi
print_success "mmcli command is available globally"

echo
echo "=== Installation Complete! ==="
echo
print_success "mmcli is now installed and available globally!"
echo
echo "Usage examples:"
echo "  mmcli \"https://youtube.com/watch?v=...\""
echo "  mmcli \"https://youtube.com/watch?v=...\" --resolution 720 --format mp4"
echo "  mmcli \"https://youtube.com/playlist?list=...\" --format mp3 --output-dir ~/Music"
echo
echo "Type 'mmcli --help' for full command reference"
echo
echo "If mmcli command is not found, restart your terminal and try again."
echo

# Make sure the script can be run
echo "To make this script executable in the future:"
echo "  chmod +x bin/install.sh"