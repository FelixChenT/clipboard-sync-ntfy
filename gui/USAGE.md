# Clipboard Sync GUI - 使用说明

## 快速开始

### 1. 启动应用

在 `gui` 目录下运行：

```bash
./start.sh
```

或者手动启动：

```bash
# 安装依赖（首次运行）
npm install
cd src/renderer && npm install && cd ../..

# 构建 React 应用
npm run build:react

# 启动应用
npm start
```

### 2. 配置剪贴板同步

1. **打开应用**：启动后会看到一个现代化的 macOS 风格界面
2. **配置发送器**：
   - 勾选"Enable Sender"
   - 设置 Ntfy Topic URL（如：`https://ntfy.sh/your_unique_topic_send`）
   - 调整轮询间隔（默认 1 秒）

3. **配置接收器**：
   - 勾选"Enable Receiver"  
   - 设置 Ntfy Server（默认：`ntfy.sh`）
   - 设置 Ntfy Topic（如：`your_unique_topic_receive`）

4. **保存配置**：点击"Save Configuration"按钮

### 3. 开始同步

1. 切换到"Status"标签页
2. 点击"Start Sync"按钮
3. 查看状态指示器确认运行状态

### 4. 查看日志

切换到"Logs"标签页可以查看实时日志输出，帮助诊断问题。

## 功能特性

- ✅ **现代化界面**：简洁的 macOS 风格设计
- ✅ **实时状态监控**：显示同步状态和进程信息
- ✅ **配置管理**：图形化配置所有参数
- ✅ **实时日志**：查看详细的运行日志
- ✅ **系统托盘**：支持后台运行和快捷操作
- ✅ **Python 集成**：无缝集成原有的 Python 同步逻辑

## 系统要求

- macOS 10.14 或更高版本
- Node.js 16 或更高版本
- Python 3.8+ （用于后端同步功能）

## 故障排除

### 应用无法启动
- 确保已安装 Node.js 16+
- 检查是否在正确的目录（gui 文件夹）
- 运行 `npm install` 重新安装依赖

### Python 进程启动失败
- 确保 Python 虚拟环境已创建（在项目根目录运行 `python3 -m venv venv`）
- 确保已安装 Python 依赖（`pip install -r requirements.txt`）
- 检查配置文件是否正确设置

### 同步不工作
- 检查网络连接
- 确认 ntfy 主题名称正确
- 查看日志标签页的错误信息

## 打包分发

要创建可分发的 macOS 应用：

```bash
npm run build
```

这将在 `dist` 文件夹中创建 `.dmg` 安装包。

## 技术架构

- **Electron**：跨平台桌面应用框架
- **React**：现代化前端界面
- **Python**：后端剪贴板同步逻辑
- **IPC**：进程间通信协调前后端
