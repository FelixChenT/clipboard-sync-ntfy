# Clipboard Sync Ntfy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[中文](README_zh.md) | [English](README.md)

使用 [ntfy.sh](https://ntfy.sh/) 在多台设备间同步剪贴板内容（文本和图片）。

**主要功能:**

*   **文本同步:** 在所有运行此脚本的设备间双向同步文本剪贴板内容。
*   **图片同步 (macOS):** 在 macOS 设备间双向同步图片剪贴板内容。在非 macOS 设备上，图片会以其 ntfy URL 的形式同步。
*   **基于 Ntfy:** 利用免费、开源的 ntfy 服务进行消息推送，无需自建服务器（也可使用自建 ntfy 服务器）。
*   **配置灵活:** 通过 YAML 文件配置 ntfy 主题、轮询间隔、超时等参数。
*   **异步高效:** 使用 `asyncio`, `websockets`, `aiohttp` 实现高效的网络通信。

**工作原理:**

脚本包含两个主要部分，可以同时运行：

1.  **发送器 (Sender):**
    *   定期检查本地剪贴板是否有新的 **文本** 内容。
    *   为了避免无限循环（A 收到 -> 写入剪贴板 -> A 又发送），它会忽略掉刚刚从 ntfy 接收并写入剪贴板的内容。
    *   检测到新的、非接收来的文本内容后，将其作为文件附件 POST 到配置的 "发送" ntfy 主题 URL。

2.  **接收器 (Receiver):**
    *   通过 WebSocket 连接到配置的 "接收" ntfy 主题。
    *   监听 ntfy 消息。
    *   如果消息包含文本附件 (`.txt`) 或纯文本消息，下载/获取文本内容并写入本地剪贴板。
    *   如果消息包含图片附件 (png, jpg, gif 等)：
        *   在 **macOS** 上：下载图片数据，并使用 AppleScript 将图片直接写入剪贴板。
        *   在 **非 macOS** 上：将图片的 ntfy URL 写入剪贴板。
    *   更新一个内部状态，标记刚刚接收到的文本内容，以便发送器可以忽略它。

**注意:** 发送器目前只发送 **文本** 内容。接收器可以接收文本和图片（macOS）。

## 先决条件

*   Python 3.8+
*   `pip` (Python 包管理器)
*   **macOS (可选):** 为了实现完整的图片剪贴板同步功能，需要 macOS 系统。在 Linux 或 Windows 上，图片将以 URL 的形式同步。

## 安装

1.  **克隆仓库:**
    ```bash
    git clone https://github.com/FelixChenT/clipboard-sync-ntfy.git
    cd clipboard-sync-ntfy
    ```
2.  **创建并激活虚拟环境 (推荐):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # 在 Windows 上使用: venv\Scripts\activate
    ```

3.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```
    *在非 macOS 系统上，`pyobjc` 相关的库会被跳过。*

## 配置

1.  **复制配置文件:**
    ```bash
    cp config/config.yaml.example config/config.yaml
    ```

2.  **编辑 `config/config.yaml`:**
    *   **`sender.ntfy_topic_url`:**  **必须修改！** 设置你用于 **发送** 剪贴板内容的 ntfy 主题 URL。例如 `https://ntfy.sh/my_clipboard_sender_abc123`。建议使用复杂、不易猜测的名称。
    *   **`receiver.ntfy_topic`:** **必须修改！** 设置你用于 **接收** 剪贴板内容的 ntfy 主题名称。例如 `my_clipboard_receiver_xyz789`。**这个主题应该与你其他设备上配置的 `sender.ntfy_topic_url` 的主题部分相对应。**
    *   **`receiver.ntfy_server`:** 如果你使用自建的 ntfy 服务器，请修改这里。
    *   根据需要调整 `poll_interval_seconds`, `request_timeout_seconds`, `logging.level` 等其他参数。
    *   确保 `sender.enabled` 和 `receiver.enabled` 设置为 `true` 以启用相应功能。

    **重要:**
    *   发送和接收通常需要不同的 ntfy 主题，以避免设备自己给自己发送消息造成混乱。
    *   **设备 A** 的 `sender.ntfy_topic_url` 应该指向 **设备 B** 的 `receiver.ntfy_topic` 所在的主题。
    *   **设备 B** 的 `sender.ntfy_topic_url` 应该指向 **设备 A** 的 `receiver.ntfy_topic` 所在的主题。

    **示例 (两台设备 A 和 B):**

    *   **设备 A (`config.yaml`)**:
        ```yaml
        sender:
          ntfy_topic_url: "https://ntfy.sh/clipboard_A_to_B"
          # ...
        receiver:
          ntfy_topic: "clipboard_B_to_A"
          # ...
        ```
    *   **设备 B (`config.yaml`)**:
        ```yaml
        sender:
          ntfy_topic_url: "https://ntfy.sh/clipboard_B_to_A"
          # ...
        receiver:
          ntfy_topic: "clipboard_A_to_B"
          # ...
        ```

## 运行

提供了 `run.sh` 脚本来方便地设置环境并启动程序。

```bash
chmod +x scripts/run.sh
./scripts/run.sh [模式] [选项]
```

脚本会自动：
1. 检查 Python 环境。
2. 检查并创建 Python 虚拟环境 (`venv`)：
   - 如果虚拟环境不存在，会创建新的虚拟环境并安装所有依赖。
   - 如果虚拟环境已存在，默认不会更新依赖（除非使用像 `--update-deps` 这样的选项）。
3. 检查配置文件：
   - 如果 `config/config.yaml` 不存在，会提示从 `config.yaml.example` 复制并自定义。
4. 启动主程序 `main.py`，并传递指定的模式。

**参数与选项:**

-   **`[模式]`** (可选): 指定运行哪些组件。此参数会作为 `--mode <值>` 传递给 `main.py`，并且将 **覆盖** 您 `config.yaml` 文件中的 `sender.enabled` 和 `receiver.enabled` 设置。可以是以下之一：
    -   `sender`: 仅启动剪贴板发送端。
    -   `receiver`: 仅启动剪贴板接收端。
    -   `both`: 同时启动发送端和接收端。
    如果省略此参数，脚本默认将 `--mode both` 传递给 `main.py`，这意味着两个组件都将被启用，除非在 `config.yaml` 中被各自的设置明确禁用（但如果使用命令行覆盖，则命令行具有优先权）。

-   **`[选项]`**:
    -   `--update-deps`: 在运行前更新 Python 依赖。此选项可以与 `[模式]` 参数结合使用。

**示例:**

-   仅运行发送端:
    ```bash
    ./scripts/run.sh sender
    ```
-   仅运行接收端:
    ```bash
    ./scripts/run.sh receiver
    ```
-   同时运行发送端和接收端 (如果未指定模式，则为默认行为):
    ```bash
    ./scripts/run.sh
    ```
    或明确指定:
    ```bash
    ./scripts/run.sh both
    ```
-   仅运行发送端并强制更新依赖:
    ```bash
    ./scripts/run.sh sender --update-deps
    ```
    或者 (注意: 对于 `run.sh`，如果指定了模式，这两个特定参数的顺序很重要)
    ```bash
    ./scripts/run.sh --update-deps sender
    ```

按 `Ctrl+C` 停止运行。

**手动运行:**
如果你不想使用 `run.sh` 脚本：
1. 创建并激活虚拟环境：
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
2. 安装依赖：
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. 确保配置文件存在：
   ```bash
   cp config/config.yaml.example config/config.yaml
   # 编辑 config.yaml 设置你的配置
   ```
4. 运行主程序：
   ```bash
   python main.py
   ```

## 代理设置

启动脚本 (`run.sh`) **不会** 自动处理网络代理。如果你的网络环境需要代理才能访问 `ntfy.sh` 或你的 ntfy 服务器，请在运行脚本 **之前** 在你的终端中设置标准的环境变量，例如：

```bash
export HTTPS_PROXY="http://your_proxy_server:port"
export ALL_PROXY="socks5://your_proxy_server:port" # 或者适用于你的代理类型
```

或者在 Python 脚本内部处理代理（目前未实现）。

## 限制与已知问题

*   **图片发送:** 当前版本 **只发送文本** 内容。接收端可以处理来自其他 ntfy 源（如手机 App）发送的图片附件。未来可以扩展发送端以支持发送图片。
*   **macOS 依赖:** 完整的图片剪贴板同步仅在 macOS 上有效。
*   **反馈循环:** 脚本内置了防止本机发送 -> 接收 -> 再发送的机制（通过 `_last_received_text` 状态），但这依赖于文本内容的精确匹配。在某些边缘情况下或快速连续操作时，仍可能出现不期望的行为。
*   **错误处理:** 虽然进行了一些错误处理，但在网络不稳定或 ntfy 服务不可用时，可能需要手动重启脚本。
*   **安全性:** 使用公共 ntfy.sh 主题意味着任何知道主题名称的人都可能看到或发送内容。对于敏感信息，请使用 [ntfy 的访问控制功能](https://docs.ntfy.sh/config/#access-control) 或自建需要认证的 ntfy 服务器。**不要在公共仓库中提交包含私有或认证信息的 `config.yaml` 文件！**

## 贡献

欢迎提交 Pull Requests 或 Issues 来改进此项目！

## 许可证

本项目采用 [MIT 许可证](LICENSE)。