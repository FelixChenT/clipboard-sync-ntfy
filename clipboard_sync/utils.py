# -*- coding: utf-8 -*-
import logging
import sys

# --- 日志设置 ---
def setup_logging(log_level_str="INFO"):
    """配置全局日志记录器"""
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # 为第三方库设置稍微安静的日志级别，除非全局是 DEBUG
    if log_level > logging.DEBUG:
        logging.getLogger("websockets").setLevel(logging.WARNING)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)

    root_logger = logging.getLogger() # 获取根 logger
    # 可以添加其他 handler，例如文件 handler
    # handler = logging.FileHandler("clipboard_sync.log")
    # formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
    # handler.setFormatter(formatter)
    # root_logger.addHandler(handler)

    return root_logger # 返回根 logger，虽然通常直接用 logging.getLogger 获取

def check_pyobjc():
    """检查 PyObjC 是否安装 (仅在 macOS 上需要)"""
    if sys.platform == 'darwin':
        try:
            import AppKit
            logging.getLogger(__name__).info("PyObjC (AppKit) found.")
            return True
        except ImportError:
            logging.getLogger(__name__).critical(
                "macOS detected but PyObjC libraries are missing. "
                "Image support will be disabled. "
                "Install them with: pip install pyobjc-core pyobjc-framework-Cocoa"
            )
            return False
    else:
        logging.getLogger(__name__).info(f"Running on non-macOS platform ({sys.platform}). PyObjC check skipped.")
        return False # 在非 macOS 上认为 PyObjC 不可用