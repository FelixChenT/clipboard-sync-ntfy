# -*- coding: utf-8 -*-
import aiohttp
import asyncio
import logging
import os
import tempfile
import datetime
# 移除 urllib.request 和 urllib.error
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("NtfyClient")

class NtfyClient:
    """Handles communication with the ntfy server (sending POST, receiving via WebSocket)."""

    # 移除 __init__ 中的 session 存储，将在方法中传递
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sender_cfg = config.get('sender', {})
        self.receiver_cfg = config.get('receiver', {})
        self.macos_cfg = config.get('macos', {})

        self.sender_url = self.sender_cfg.get('ntfy_topic_url')
        self.sender_timeout_config = self.sender_cfg.get('request_timeout_seconds', 15) # 配置中的超时
        self.filename_prefix = self.sender_cfg.get('filename_prefix', "clipboard_")

        self.receiver_server = self.receiver_cfg.get('ntfy_server')
        self.receiver_timeout_config = self.receiver_cfg.get('request_timeout_seconds', 15) # 配置中的超时
        self.image_uti_map = self.macos_cfg.get('image_uti_map', {})

    # 修改 post_text_as_file 以使用 aiohttp
    async def post_text_as_file(self, session: aiohttp.ClientSession, text_content: str) -> bool:
        """
        Asynchronously posts text content as a file attachment to the configured ntfy sender URL using aiohttp.
        """
        if not self.sender_url:
            logger.error("Sender URL not configured. Cannot post text.")
            return False
        if not text_content:
            logger.warning("Attempted to post empty text content.")
            return False

        temp_file_path = None
        try:
            # Create a temporary file to hold the text content (synchronous part)
            # Use a context manager for cleaner temp file handling
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt',
                                             delete=False, prefix=self.filename_prefix) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(text_content)
                logger.debug(f"Text content written to temporary file: {temp_file_path}")
                temp_filename_base = os.path.basename(temp_file_path) # Get filename before closing

            # Ensure Filename header is ASCII or Latin-1 compatible
            safe_filename = temp_filename_base.encode('ascii', errors='ignore').decode('ascii')
            if not safe_filename:
                safe_filename = "clipboard.txt"

            headers = {
                'Filename': safe_filename,
                'Content-Type': 'text/plain; charset=utf-8', # Explicitly set for clarity
                'Title': f'Clipboard Text ({datetime.datetime.now().strftime("%H:%M:%S")})',
            }

            # Read the content back (synchronous part)
            with open(temp_file_path, 'rb') as f_read:
                file_content_bytes = f_read.read()

            logger.info(f"Attempting to POST file: {safe_filename} ({len(file_content_bytes)} bytes) to {self.sender_url}")

            # --- Asynchronous POST using aiohttp ---
            request_timeout = aiohttp.ClientTimeout(total=self.sender_timeout_config)
            async with session.post(
                self.sender_url,
                data=file_content_bytes,
                headers=headers,
                timeout=request_timeout
            ) as response:
                status_code = response.status
                response_text = await response.text() # Read response for logging

                if 200 <= status_code < 300:
                    logger.info(f"Successfully POSTed to ntfy. Status: {status_code}.")
                    return True
                else:
                    logger.error(f"Error POSTing to ntfy. Status: {status_code}")
                    logger.error(f"Ntfy Response: {response_text[:500]}{'...' if len(response_text)>500 else ''}")
                    return False

        except aiohttp.ClientResponseError as e:
             logger.error(f"HTTP error during POST: {e.status} {e.message} to {self.sender_url}")
             return False
        except aiohttp.ClientError as e: # Includes connection errors, etc.
            logger.error(f"Network error during POST: {e} to {self.sender_url}")
            return False
        except asyncio.TimeoutError:
            logger.error(f"Timeout ({self.sender_timeout_config}s) during POST to {self.sender_url}")
            return False
        except FileNotFoundError:
             logger.error(f"Error: Temporary file not found at {temp_file_path}")
             return False
        except Exception as e:
            logger.error(f"Unexpected error during text post: {e}", exc_info=True)
            return False
        finally:
            # Clean up the temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    logger.debug(f"Temporary file deleted: {temp_file_path}")
                except OSError as e:
                    logger.error(f"Error deleting temporary file {temp_file_path}: {e}")

    # --- _execute_post_request is no longer needed ---
    # def _execute_post_request(...)

    # download_attachment remains mostly the same, but uses the passed session
    async def download_attachment(self, session: aiohttp.ClientSession, url: str) -> Optional[Tuple[bytes, Optional[str]]]:
        """
        Asynchronously downloads attachment content (bytes) and detects content type.
        Handles relative URLs based on receiver config.
        Returns (content_bytes, content_type) or None on failure.
        """
        full_url = self._resolve_url(url)
        if not full_url:
            logger.error(f"Could not resolve attachment URL: {url}")
            return None

        logger.info(f"Attempting to download attachment from: {full_url}")
        try:
            # Use the passed session and configured timeout
            request_timeout = aiohttp.ClientTimeout(total=self.receiver_timeout_config)
            async with session.get(full_url, timeout=request_timeout) as response:
                response.raise_for_status() # Raise exception for bad status codes (4xx, 5xx)
                content_bytes = await response.read()
                content_type = response.headers.get('Content-Type', '').lower()
                logger.info(f"Successfully downloaded attachment. Size: {len(content_bytes)} bytes, Type: {content_type or 'Unknown'}.")
                return content_bytes, content_type
        except aiohttp.ClientResponseError as e:
             logger.error(f"HTTP error downloading attachment: {e.status} {e.message} from {full_url}")
             return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error downloading attachment: {e} from {full_url}")
            return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout ({self.receiver_timeout_config}s) downloading attachment from {full_url}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading attachment: {e} from {full_url}", exc_info=True)
            return None


    def decode_text_content(self, content_bytes: bytes, url: str = "N/A") -> Optional[str]:
        """
        Attempts to decode byte content into text using common encodings.
        Tries UTF-8 first, then GBK as a fallback.
        """
        if not content_bytes:
            return "" # Return empty string for empty bytes

        encodings_to_try = ['utf-8', 'gbk'] # Add more if needed, e.g., 'latin-1'

        for encoding in encodings_to_try:
            try:
                text = content_bytes.decode(encoding)
                logger.info(f"Successfully decoded text attachment using '{encoding}'. URL: {url}")
                return text
            except UnicodeDecodeError:
                logger.debug(f"Failed to decode text attachment using '{encoding}'. URL: {url}")
            except Exception as e:
                 logger.error(f"Error during decoding with '{encoding}': {e}. URL: {url}", exc_info=True)


        # If all attempts fail, force decode with utf-8 ignoring errors
        logger.warning(f"All decoding attempts failed for attachment from {url}. Forcing decode with 'utf-8' (ignore errors).")
        final_text = content_bytes.decode('utf-8', errors='ignore')
        return final_text


    def _resolve_url(self, url: str) -> Optional[str]:
        """Resolves potentially relative attachment URLs based on ntfy server config."""
        if not url:
            return None
        if url.startswith(('http://', 'https://')):
            return url
        if self.receiver_server:
            base_url = f"https://{self.receiver_server}" # Assume https by default
            if self.receiver_server.startswith("http://"):
                 base_url = f"http://{self.receiver_server}"

            if url.startswith('//'):
                return f"{base_url.split(':', 1)[0]}:{url}" # e.g. https:// + //server.com/path
            elif url.startswith('/'):
                return f"{base_url}{url}" # e.g. https://server.com + /path/to/file
            else:
                 # This case is ambiguous (could be just domain or relative path)
                 # Assume it's a path relative to root for now
                 logger.warning(f"Ambiguous relative URL '{url}'. Assuming relative to server root: {base_url}/{url}")
                 return f"{base_url}/{url}"
        else:
            logger.error("Cannot resolve relative URL because receiver.ntfy_server is not configured.")
            return None

    def is_image_attachment(self, filename: Optional[str], content_type: Optional[str]) -> bool:
        """Checks if an attachment is likely an image based on filename or content type."""
        if not filename and not content_type:
            return False

        # Check by filename extension
        if filename:
            lower_name = filename.lower()
            file_ext = os.path.splitext(lower_name)[1]
            if file_ext in self.image_uti_map:
                logger.debug(f"Detected image by extension '{file_ext}' in filename '{filename}'.")
                return True

        # Check by content type
        if content_type and content_type.startswith('image/'):
             logger.debug(f"Detected image by Content-Type '{content_type}'.")
             return True

        return False

    def is_text_attachment(self, filename: Optional[str], content_type: Optional[str]) -> bool:
        """Checks if an attachment is likely a text file."""
         # Check by filename extension
        if filename and filename.lower().endswith('.txt'):
            logger.debug(f"Detected text file by extension '.txt' in filename '{filename}'.")
            return True
        # Check by content type
        if content_type and content_type.startswith('text/plain'):
             logger.debug(f"Detected text file by Content-Type '{content_type}'.")
             return True
        return False