# Clipboard Sync Ntfy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[中文](README_zh.md) | [English](README.md)

---

**一个由 [ntfy.sh](https://ntfy.sh/) 驱动的跨平台剪贴板同步工具，并为 macOS 提供了精美的图形用户界面。**

在您的多台设备之间无缝同步剪贴板内容（文本和图片）。您可以使用美观、原生的 macOS GUI 获得直观的体验，也可以在任何平台（macOS、Linux、Windows）上直接运行强大的 Python 后端。

![Clipboard Sync GUI 截图](gui/assets/screenshot.png)
*(macOS GUI 应用截图)*

## 功能特性

### 🌟 图形界面 (GUI for macOS)
- **原生 macOS 界面**: 干净、现代且直观的用户界面。
- **轻松配置**: 通过用户友好的面板管理所有设置，包括 ntfy 主题和服务器地址，无需再手动编辑 YAML 文件。
- **实时状态与日志**: 直接在应用内监控同步状态、查看运行中的进程 ID，并浏览实时日志。
- **系统托盘集成**: 在后台安静运行，可通过系统托盘图标快速访问。
- **启停控制**: 只需单击一下，即可轻松启动和停止同步服务。

### ⚙️ 核心引擎 (跨平台)
- **文本同步**: 在所有连接的设备之间进行双向文本剪贴板同步。
- **图片同步 (macOS 原生)**: 在 macOS 设备之间进行双向图片剪贴板同步。在非 macOS 设备上，图片将以 ntfy URL 的形式同步。
- **基于 Ntfy**: 利用免费、开源的 [ntfy.sh](https://ntfy.sh/) 服务，无需自建服务器即可同步。同时也支持使用自建的 ntfy 服务器。
- **高效异步**: 使用 Python 的 `asyncio`、`websockets` 和 `aiohttp` 构建，实现高效率和低资源占用。
- **灵活**: 可以在任何主流操作系统上作为独立的命令行脚本运行。

## 如何使用

有两种方式来使用本工具：

### 方法一：GUI 应用程序 (macOS 用户推荐)

这是在 macOS 上最简单的入门方式。

1.  **下载**: 从 [**Releases**](https://github.com/FelixChenT/clipboard-sync-ntfy/releases) 页面下载最新的 `.dmg` 文件。
2.  **安装**: 打开 `.dmg` 文件，将 `Clipboard Sync.app` 拖到您的“应用程序”文件夹中。
3.  **启动与配置**:
    *   打开应用。
    *   进入“配置” (Configuration) 标签页。
    *   设置您独一无二的“发送主题URL” (Send Topic URL) 和“接收主题” (Receive Topic)。请务必阅读下方的 [配置详情](#配置详情) 以正确设置主题。
    *   点击“保存” (Save)。
4.  **开始同步**: 进入“控制” (Control) 标签页，点击“启动同步” (Start Sync)。应用现在将在后台运行，并可通过系统托盘图标访问。

### 方法二：命令行脚本 (所有平台)

适用于 Linux、Windows 用户，或在 macOS 上进行高级的无头配置。

#### 1. 先决条件
*   Python 3.8+
*   `pip` (Python 包管理器)

#### 2. 安装
```bash
# 克隆仓库
git clone https://github.com/FelixChenT/clipboard-sync-ntfy.git
cd clipboard-sync-ntfy

# 创建并激活虚拟环境 (推荐)
python3 -m venv venv
source venv/bin/activate
# 在 Windows 上，使用: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```
*在非 macOS 系统上，与 `pyobjc` 相关的库会自动跳过安装。*

#### 3. 配置
复制配置文件示例：
```bash
cp config/config.yaml.example config/config.yaml
```
现在，用您的文本编辑器打开 `config/config.yaml`。请参考下方的 [配置详情](#配置详情) 来设置您的主题。

#### 4. 运行脚本
为了方便使用，项目提供了一个 `run.sh` 辅助脚本。
```bash
# 赋予脚本执行权限
chmod +x scripts/run.sh

# 同时运行发送器和接收器 (默认)
./scripts/run.sh

# 或仅运行发送器
./scripts/run.sh sender

# 或仅运行接收器
./scripts/run.sh receiver
```
按 `Ctrl+C` 停止运行。

## 配置详情

为了在 **设备 A** 和 **设备 B** 之间同步，您必须将它们配置为互相监听。**请勿对发送和接收使用相同的主题。**

*   **设备 A** 应该发送到 **设备 B** 正在接收的主题。
*   **设备 B** 应该发送到 **设备 A** 正在接收的主题。

**配置示例:**

*   **设备 A (`config.yaml` 或 GUI 配置):**
    *   `sender.ntfy_topic_url`: `https://ntfy.sh/topic_A_to_B`
    *   `receiver.ntfy_topic`: `topic_B_to_A`

*   **设备 B (`config.yaml` 或 GUI 配置):**
    *   `sender.ntfy_topic_url`: `https://ntfy.sh/topic_B_to_A`
    *   `receiver.ntfy_topic`: `topic_A_to_B`

## 开发者指南

想要贡献代码或从源码构建？请看这里。

### 后端设置
遵循 [方法二](#方法二命令行脚本-所有平台) 中的步骤来设置 Python 环境。

### GUI 设置 (macOS)
GUI 是一个 Electron/React 应用。

1.  **先决条件**: Node.js (v16+) 和 npm。
2.  **安装依赖**:
    ```bash
    # 安装 Electron 的根依赖
    npm install

    # 安装 React 前端的依赖
    cd gui/src/renderer
    npm install
    cd ../../..
    ```
3.  **以开发模式运行**:
    此命令会启动 React 开发服务器和 Electron 应用，并为 UI 启用热重载。
    ```bash
    npm run dev
    ```

### 构建应用
要从源码构建原生的 macOS `.dmg` 文件：
```bash
# 此命令会先构建 React 应用，然后用 Electron 打包
npm run build
```
输出文件将位于 `gui/dist` 目录中。

## 工作原理

本应用包含两个主要组件：

1.  **发送器 (Sender)**: 定期检查本地剪贴板是否有新的**文本**内容。为防止无限循环，它会忽略刚刚接收到的内容。当检测到新内容时，会将其发送到配置的 ntfy 主题。
2.  **接收器 (Receiver)**: 与 ntfy 主题维持一个持久的 WebSocket 连接。当收到消息时，它会处理消息并将其写入本地剪贴板。它能处理文本和图片（在 macOS 上，图片被直接写入剪贴板；在其他系统上，则写入图片的 URL）。

## 限制与安全

*   **图片发送**: 核心的 Python 发送器目前**只发送文本**。接收器可以处理从其他来源（如 ntfy 手机 App）发送的图片。
*   **安全性**: 使用公共的 ntfy 主题意味着任何知道主题名称的人都可能拦截您的剪贴板数据。对于敏感信息，请使用带有[访问控制](https://docs.ntfy.sh/config/#access-control)的自建 ntfy 服务器。**切勿将包含私有主题的 `config.yaml` 文件提交到公共代码库。**

## 贡献

欢迎提交 Pull Requests 和 Issues！

## 许可证

本项目采用 [MIT 许可证](LICENSE)。