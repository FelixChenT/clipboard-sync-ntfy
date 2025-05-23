# Clipboard Sync Ntfy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[中文](README_zh.md) | [English](README.md)

Synchronize clipboard content (text and images) across multiple devices using [ntfy.sh](https://ntfy.sh/).

**Key Features:**

*   **Text Sync:** Bidirectional text clipboard synchronization between all devices running this script.
*   **Image Sync (macOS):** Bidirectional image clipboard synchronization between macOS devices. On non-macOS devices, images are synced as ntfy URLs.
*   **Ntfy-based:** Uses the free, open-source ntfy service for message pushing, no need for self-hosted server (though self-hosted ntfy server is supported).
*   **Flexible Configuration:** Configure ntfy topics, polling intervals, timeouts, and other parameters via YAML file.
*   **Async Efficient:** Implements efficient network communication using `asyncio`, `websockets`, and `aiohttp`.

**How It Works:**

The script consists of two main components that can run simultaneously:

1.  **Sender:**
    *   Periodically checks local clipboard for new **text** content.
    *   To prevent infinite loops (A receives -> writes to clipboard -> A sends again), it ignores content that was just received from ntfy and written to the clipboard.
    *   When new, non-received text content is detected, it POSTs it as a file attachment to the configured "send" ntfy topic URL.

2.  **Receiver:**
    *   Connects to the configured "receive" ntfy topic via WebSocket.
    *   Listens for ntfy messages.
    *   If the message contains a text attachment (`.txt`) or plain text message, downloads/retrieves the text content and writes it to the local clipboard.
    *   If the message contains an image attachment (png, jpg, gif, etc.):
        *   On **macOS**: Downloads the image data and uses AppleScript to write it directly to the clipboard.
        *   On **non-macOS**: Writes the image's ntfy URL to the clipboard.
    *   Updates an internal state to mark the recently received text content so the sender can ignore it.

**Note:** The sender currently only sends **text** content. The receiver can handle both text and images (macOS).

## Prerequisites

*   Python 3.8+
*   `pip` (Python package manager)
*   **macOS (optional):** Required for full image clipboard sync functionality. On Linux or Windows, images will be synced as URLs.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/FelixChenT/clipboard-sync-ntfy.git
    cd clipboard-sync-ntfy
    ```

2.  **Create and activate virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows use: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *On non-macOS systems, `pyobjc`-related libraries will be skipped.*

## Configuration

1.  **Copy the configuration file:**
    ```bash
    cp config/config.yaml.example config/config.yaml
    ```

2.  **Edit `config/config.yaml`:**
    *   **`sender.ntfy_topic_url`:** **Must modify!** Set your ntfy topic URL for **sending** clipboard content. For example, `https://ntfy.sh/my_clipboard_sender_abc123`. Use a complex, hard-to-guess name.
    *   **`receiver.ntfy_topic`:** **Must modify!** Set your ntfy topic name for **receiving** clipboard content. For example, `my_clipboard_receiver_xyz789`. **This topic should correspond to the topic part of the `sender.ntfy_topic_url` configured on your other devices.**
    *   **`receiver.ntfy_server`:** Modify this if you're using a self-hosted ntfy server.
    *   Adjust `poll_interval_seconds`, `request_timeout_seconds`, `logging.level`, and other parameters as needed.
    *   Ensure `sender.enabled` and `receiver.enabled` are set to `true` to enable respective functionality.

    **Important:**
    *   Sending and receiving typically need different ntfy topics to prevent devices from sending messages to themselves.
    *   **Device A**'s `sender.ntfy_topic_url` should point to the topic where **Device B**'s `receiver.ntfy_topic` is listening.
    *   **Device B**'s `sender.ntfy_topic_url` should point to the topic where **Device A**'s `receiver.ntfy_topic` is listening.

    **Example (two devices A and B):**

    *   **Device A (`config.yaml`)**:
        ```yaml
        sender:
          ntfy_topic_url: "https://ntfy.sh/clipboard_A_to_B"
          # ...
        receiver:
          ntfy_topic: "clipboard_B_to_A"
          # ...
        ```
    *   **Device B (`config.yaml`)**:
        ```yaml
        sender:
          ntfy_topic_url: "https://ntfy.sh/clipboard_B_to_A"
          # ...
        receiver:
          ntfy_topic: "clipboard_A_to_B"
          # ...
        ```

## Running

A `run.sh` script is provided to conveniently set up the environment and start the program.

```bash
chmod +x scripts/run.sh
./scripts/run.sh [mode] [options]
```

The script will automatically:
1. Check Python environment.
2. Check and create Python virtual environment (`venv`):
   - If the virtual environment doesn't exist, creates a new one and installs all dependencies.
   - If the virtual environment exists, won't update dependencies by default (unless an option like `--update-deps` is used).
3. Check configuration file:
   - If `config/config.yaml` doesn't exist, prompts to copy from `config.yaml.example` and customize.
4. Start the main program `main.py`, passing the specified mode.

**Arguments & Options:**

-   **`[mode]`** (optional): Specifies which components to run. This argument is passed to `main.py` as `--mode <value>` and will **override** the `sender.enabled` and `receiver.enabled` settings in your `config.yaml`. Can be one of:
    -   `sender`: Starts only the clipboard sender.
    -   `receiver`: Starts only the clipboard receiver.
    -   `both`: Starts both the sender and receiver.
    If omitted, the script defaults to passing `--mode both` to `main.py`, meaning both components will be enabled unless explicitly disabled by their individual settings in `config.yaml` (however, the command-line override takes precedence if used).

-   **`[options]`**:
    -   `--update-deps`: Updates Python dependencies before running. This can be combined with the `[mode]` argument.

**Examples:**

-   Run only the sender:
    ```bash
    ./scripts/run.sh sender
    ```
-   Run only the receiver:
    ```bash
    ./scripts/run.sh receiver
    ```
-   Run both sender and receiver (this is the default behavior if no mode is specified):
    ```bash
    ./scripts/run.sh
    ```
    or explicitly:
    ```bash
    ./scripts/run.sh both
    ```
-   Run only the sender and force update dependencies:
    ```bash
    ./scripts/run.sh sender --update-deps
    ```
    or (note: for `run.sh` the order of these two specific arguments matters if mode is specified)
    ```bash
    ./scripts/run.sh --update-deps sender
    ```

Press `Ctrl+C` to stop running.

**Manual Running:**
If you don't want to use the `run.sh` script:
1. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Ensure configuration file exists:
   ```bash
   cp config/config.yaml.example config/config.yaml
   # Edit config.yaml with your settings
   ```
4. Run the main program:
   ```bash
   python main.py
   ```

## Proxy Settings

The startup script (`run.sh`) does **not** automatically handle network proxies. If your network environment requires a proxy to access `ntfy.sh` or your ntfy server, please set standard environment variables in your terminal **before** running the script, for example:

```bash
export HTTPS_PROXY="http://your_proxy_server:port"
export ALL_PROXY="socks5://your_proxy_server:port" # or appropriate for your proxy type
```

Or handle proxies within the Python script (not currently implemented).

## Limitations and Known Issues

*   **Image Sending:** The current version **only sends text** content. The receiver can handle image attachments from other ntfy sources (like mobile apps). Future versions may extend the sender to support sending images.
*   **macOS Dependencies:** Full image clipboard sync only works on macOS.
*   **Feedback Loop:** The script has built-in prevention against local send -> receive -> send loops (via `_last_received_text` state), but this relies on exact text content matching. Unexpected behavior may still occur in edge cases or during rapid consecutive operations.
*   **Error Handling:** While some error handling is implemented, manual script restart may be needed during network instability or ntfy service unavailability.
*   **Security:** Using public ntfy.sh topics means anyone who knows the topic name can potentially see or send content. For sensitive information, use [ntfy's access control features](https://docs.ntfy.sh/config/#access-control) or set up an authenticated self-hosted ntfy server. **Never commit `config.yaml` files containing private or authentication information to public repositories!**

## Contributing

Pull Requests and Issues are welcome to improve this project!

## License

This project is licensed under the [MIT License](LICENSE).