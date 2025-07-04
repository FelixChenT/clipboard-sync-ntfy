# CLAUDE.md

此文件指导Claude Code (claude.ai/code)在此代码库中的工作。

## 常用命令
- 运行剪贴板同步工具：
  ```bash
  ./run.sh --sender    # 只运行发送端
  ./run.sh --receiver  # 只运行接收端
  ./run.sh --both      # 同时运行发送和接收
  ```

## 架构概述
1. **sender.py**：
   - 监听本地剪贴板变化
   - 通过ntfy.sh发送剪贴板内容到指定主题
2. **receiver.py**：
   - 订阅ntfy.sh主题
   - 将接收到的内容设置到本地剪贴板
3. 使用`pyperclip`处理剪贴板操作，`requests`处理HTTP请求

## 依赖
- Python 3.x
- 必要包：`pyperclip`, `requests`, `pynput`

## 配置提示
1. 在ntfy.sh创建私有主题
2. 设置环境变量：
   ```bash
   export NTFY_TOPIC=your_topic
   export NTFY_TOKEN=your_token
   ```