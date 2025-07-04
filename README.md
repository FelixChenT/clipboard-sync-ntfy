# Clipboard Sync Ntfy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[中文](README_zh.md) | [English](README.md)

---

**A cross-platform clipboard synchronization tool powered by [ntfy.sh](https://ntfy.sh/), with a polished GUI for macOS.**

Synchronize your clipboard (text and images) across multiple devices seamlessly. Use the beautiful native macOS GUI for an intuitive experience, or run the powerful Python backend directly on any platform (macOS, Linux, Windows).

![Screenshot of Clipboard Sync GUI](gui/assets/screenshot.png)
*(Screenshot of the macOS GUI)*

## Features

### 🌟 GUI (macOS)
- **Native macOS Interface**: A clean, modern, and intuitive user interface.
- **Easy Configuration**: Manage all settings, including ntfy topics and server details, from a user-friendly panel. No more manual YAML editing.
- **Live Status & Logs**: Monitor the sync status, see the running process ID, and view live logs directly within the app.
- **System Tray Integration**: Runs discreetly in the background with a system tray icon for quick access.
- **Start/Stop Control**: Easily start and stop the sync service with a single click.

### ⚙️ Core Engine (Cross-Platform)
- **Text Sync**: Bidirectional text clipboard synchronization between all connected devices.
- **Image Sync (macOS Native)**: Bidirectional image clipboard synchronization between macOS devices. On non-macOS devices, images are synced as ntfy URLs.
- **Ntfy-based**: Leverages the free and open-source [ntfy.sh](https://ntfy.sh/) service, allowing you to sync without your own server. Self-hosted ntfy is also supported.
- **Efficient & Asynchronous**: Built with Python's `asyncio`, `websockets`, and `aiohttp` for high efficiency and low resource usage.
- **Flexible**: Can be run as a standalone command-line script on any major OS.

## How to Use

There are two ways to use Clipboard Sync Ntfy:

### Method 1: The GUI Application (Recommended for macOS)

This is the easiest way to get started on macOS.

1.  **Download**: Grab the latest `.dmg` file from the [**Releases**](https://github.com/FelixChenT/clipboard-sync-ntfy/releases) page.
2.  **Install**: Open the `.dmg` and drag `Clipboard Sync.app` to your Applications folder.
3.  **Launch & Configure**:
    *   Open the app.
    *   Go to the "Configuration" tab.
    *   Set your unique "Send Topic URL" and "Receive Topic". See [Configuration Details](#configuration-details) for a crucial guide on setting up topics correctly.
    *   Click "Save".
4.  **Start Syncing**: Go to the "Control" tab and click "Start Sync". The app will now run in the background, accessible from your system tray.

### Method 2: The Command-Line Script (All Platforms)

Use this method for Linux, Windows, or for advanced headless setups on macOS.

#### 1. Prerequisites
*   Python 3.8+
*   `pip` (Python package manager)

#### 2. Installation
```bash
# Clone the repository
git clone https://github.com/FelixChenT/clipboard-sync-ntfy.git
cd clipboard-sync-ntfy

# Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
# On Windows, use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```
*On non-macOS systems, `pyobjc`-related libraries will be skipped automatically.*

#### 3. Configuration
Copy the example config file:
```bash
cp config/config.yaml.example config/config.yaml
```
Now, edit `config/config.yaml` with your text editor. See [Configuration Details](#configuration-details) below for a guide on setting up your topics.

#### 4. Running the Script
A helper script `run.sh` is provided for convenience.
```bash
# Make the script executable
chmod +x scripts/run.sh

# Run both sender and receiver (default)
./scripts/run.sh

# Or run only the sender
./scripts/run.sh sender

# Or run only the receiver
./scripts/run.sh receiver
```
Press `Ctrl+C` to stop.

## Configuration Details

To sync between two devices, **Device A** and **Device B**, you must configure them to listen to each other. **Do not use the same topic for sending and receiving.**

*   **Device A** should send to the topic that **Device B** is receiving from.
*   **Device B** should send to the topic that **Device A** is receiving from.

**Example Setup:**

*   **Device A (`config.yaml` or GUI Config):**
    *   `sender.ntfy_topic_url`: `https://ntfy.sh/topic_A_to_B`
    *   `receiver.ntfy_topic`: `topic_B_to_A`

*   **Device B (`config.yaml` or GUI Config):**
    *   `sender.ntfy_topic_url`: `https://ntfy.sh/topic_B_to_A`
    *   `receiver.ntfy_topic`: `topic_A_to_B`

## For Developers

Want to contribute or build from source? Here’s how.

### Backend Setup
Follow the steps in [Method 2](#method-2-the-command-line-script-all-platforms) to set up the Python environment.

### GUI Setup (macOS)
The GUI is an Electron/React application.

1.  **Prerequisites**: Node.js (v16+) and npm.
2.  **Install Dependencies**:
    ```bash
    # Install root dependencies for Electron
    npm install

    # Install dependencies for the React frontend
    cd gui/src/renderer
    npm install
    cd ../../..
    ```
3.  **Run in Development Mode**:
    This command starts the React dev server and the Electron app, enabling hot-reloading for the UI.
    ```bash
    npm run dev
    ```

### Building the Application
To build the native macOS `.dmg` file from source:
```bash
# This command builds the React app and then packages it with Electron
npm run build
```
The output will be in the `gui/dist` directory.

## How It Works

The application consists of two main components:

1.  **Sender**: Periodically checks the local clipboard for new **text** content. To prevent infinite loops, it ignores content that was just received. When new content is detected, it's sent to the configured ntfy topic.
2.  **Receiver**: Maintains a persistent WebSocket connection to its ntfy topic. When a message arrives, it's processed and written to the local clipboard. It handles both text and images (on macOS, images are placed directly on the clipboard; on other systems, the image URL is used).

## Limitations & Security

*   **Image Sending**: The core Python sender currently **only sends text**. The receiver can handle images sent from other sources (like the ntfy mobile app).
*   **Security**: Using public ntfy topics means anyone with the topic name can intercept your clipboard data. For sensitive information, use a self-hosted ntfy server with [access control](https://docs.ntfy.sh/config/#access-control). **Never commit a `config.yaml` file with private topics to a public repository.**

## Contributing

Pull Requests and Issues are welcome!

## License

This project is licensed under the [MIT License](LICENSE).