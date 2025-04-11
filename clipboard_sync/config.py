# -*- coding: utf-8 -*-
import yaml
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Optional[Dict[str, Any]]:
    """加载 YAML 配置文件"""
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found at: {config_path}")
        logger.error("Please copy 'config/config.yaml.example' to 'config/config.yaml' and fill in your details.")
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded successfully from: {config_path}")
        # TODO: Add more robust validation here if needed (e.g., using Pydantic)
        if not validate_config(config):
             logger.error("Configuration validation failed. Please check your config.yaml.")
             return None
        return config
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file {config_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading configuration: {e}", exc_info=True)
        return None

def validate_config(config: Dict[str, Any]) -> bool:
    """简单的配置验证"""
    if not isinstance(config, dict):
        logger.error("Config root is not a dictionary.")
        return False

    # Sender validation
    sender_cfg = config.get('sender')
    if sender_cfg and sender_cfg.get('enabled'):
        if not sender_cfg.get('ntfy_topic_url') or "YOUR_SEND_TOPIC_HERE" in sender_cfg['ntfy_topic_url']:
            logger.error("Sender is enabled but 'sender.ntfy_topic_url' is missing or not set.")
            return False
        if not isinstance(sender_cfg.get('poll_interval_seconds', 1.0), (int, float)) or sender_cfg['poll_interval_seconds'] <= 0:
            logger.error("Invalid 'sender.poll_interval_seconds'. Must be a positive number.")
            return False

    # Receiver validation
    receiver_cfg = config.get('receiver')
    if receiver_cfg and receiver_cfg.get('enabled'):
        if not receiver_cfg.get('ntfy_topic') or "YOUR_RECEIVE_TOPIC_HERE" in receiver_cfg['ntfy_topic']:
            logger.error("Receiver is enabled but 'receiver.ntfy_topic' is missing or not set.")
            return False
        if not receiver_cfg.get('ntfy_server'):
            logger.error("Receiver is enabled but 'receiver.ntfy_server' is missing.")
            return False
        if not isinstance(receiver_cfg.get('reconnect_delay_seconds', 5), (int, float)) or receiver_cfg['reconnect_delay_seconds'] <= 0:
            logger.error("Invalid 'receiver.reconnect_delay_seconds'. Must be a positive number.")
            return False

    # Logging validation
    log_cfg = config.get('logging')
    if log_cfg and log_cfg.get('level'):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_cfg['level'].upper() not in valid_levels:
            logger.error(f"Invalid 'logging.level': {log_cfg['level']}. Must be one of {valid_levels}.")
            return False

    logger.debug("Configuration validation passed.")
    return True

# --- 获取具体配置项的辅助函数 ---

def get_sender_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return config.get('sender') if config else None

def get_receiver_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return config.get('receiver') if config else None

def get_logging_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return config.get('logging') if config else None

def get_macos_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return config.get('macos') if config else None

def get_websocket_url(config: Dict[str, Any]) -> Optional[str]:
    """构造 WebSocket URL"""
    rcv_cfg = get_receiver_config(config)
    if not rcv_cfg or not rcv_cfg.get('enabled'):
        return None
    server = rcv_cfg.get('ntfy_server')
    topic = rcv_cfg.get('ntfy_topic')
    if server and topic:
        protocol = "wss" if not server.startswith("http://") else "ws" # 简单处理 http vs https
        clean_server = server.replace("https://", "").replace("http://", "")
        return f"{protocol}://{clean_server}/{topic}/ws"
    return None