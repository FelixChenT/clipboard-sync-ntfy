# Clipboard Sync GUI

A modern macOS GUI application for the Clipboard Sync Ntfy project.

## Features

- **Intuitive Interface**: Clean, modern macOS-style interface
- **Real-time Status**: Live monitoring of sync status and process information
- **Configuration Management**: Easy-to-use configuration panel for all settings
- **Live Logs**: Real-time log viewing with syntax highlighting
- **System Tray**: Background operation with system tray integration
- **Native macOS App**: Packaged as a native macOS application

## Development

### Prerequisites

- Node.js 16 or later
- npm or yarn
- Python 3.8+ (for the backend sync functionality)

### Setup

1. Install dependencies:
```bash
npm install
```

2. Install React app dependencies:
```bash
cd src/renderer && npm install
```

3. Start development:
```bash
npm run dev
```

### Building

To build the application for distribution:

```bash
npm run build
```

This will create a distributable macOS app in the `dist` folder.

## Architecture

- **Electron Main Process**: Manages windows, system tray, and Python subprocess
- **React Renderer**: Provides the user interface
- **Python Backend**: The original clipboard sync functionality
- **IPC Communication**: Secure communication between frontend and backend

## Configuration

The app manages the same configuration as the command-line version, stored in `config/config.yaml`. The GUI provides an intuitive interface for editing all settings:

- Sender/Receiver enable/disable
- Ntfy server and topic configuration
- Polling intervals and timeouts
- Logging levels
- macOS-specific settings

## System Requirements

- macOS 10.14 or later
- 64-bit Intel or Apple Silicon processor

## License

MIT License - see the main project LICENSE file for details.
