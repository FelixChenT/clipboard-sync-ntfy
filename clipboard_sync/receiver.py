# -*- coding: utf-8 -*-
import asyncio
import websockets
import json
import logging
import aiohttp # Keep aiohttp import
import os
import socket # Import socket for gaierror
from typing import Dict, Any, Optional

from .clipboard_manager import ClipboardManager
from .ntfy_client import NtfyClient
from .config import get_websocket_url

logger = logging.getLogger("Receiver")

class NtfyReceiver:
    """Listens to ntfy via WebSocket and updates the local clipboard."""

    def __init__(self, config: Dict[str, Any], clipboard_manager: ClipboardManager, ntfy_client: NtfyClient, shared_state: Dict, session: aiohttp.ClientSession):
        """
        Initializes the NtfyReceiver.

        Args:
            config: The application configuration dictionary.
            clipboard_manager: An instance of ClipboardManager.
            ntfy_client: An instance of NtfyClient.
            shared_state: A dictionary for shared state between components (e.g., _last_received_text).
            session: An active aiohttp.ClientSession for network requests.
        """
        self.config = config
        self.receiver_cfg = config.get('receiver', {})
        self.clipboard = clipboard_manager
        self.ntfy_client = ntfy_client
        self.shared_state = shared_state
        self.session = session # Store the shared session

        self.enabled = self.receiver_cfg.get('enabled', False)
        self.websocket_url = get_websocket_url(config)
        self.reconnect_delay = int(self.receiver_cfg.get('reconnect_delay_seconds', 5))
        self.is_macos_image_support = clipboard_manager.image_support_enabled

        if not self.enabled:
            logger.info("Ntfy Receiver is disabled in the configuration.")
        elif not self.websocket_url:
            logger.error("Receiver is enabled but WebSocket URL could not be determined (check server/topic). Disabling receiver.")
            self.enabled = False
        elif not self.session:
             logger.error("Receiver requires an aiohttp ClientSession but none was provided. Disabling receiver.")
             self.enabled = False
        else:
             logger.info(f"Ntfy Receiver initialized. Listening on: {self.websocket_url}")
             if self.is_macos_image_support:
                 logger.info("macOS image support is enabled.")


    async def run(self):
        """Starts the WebSocket listening loop with reconnection logic."""
        if not self.enabled:
            return

        # Use the passed session, do not create a new one locally
        while self.enabled: # Loop continues as long as enabled and no fatal error/cancellation
            websocket = None # Ensure websocket is None initially for finally block
            try:
                logger.info(f"Attempting to connect to WebSocket: {self.websocket_url}")
                # Configure connection timeout for websockets using receiver's timeout config
                connect_timeout = self.ntfy_client.receiver_timeout_config
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.websocket_url,
                        ping_interval=20,
                        ping_timeout=20
                    ),
                    timeout=connect_timeout
                )
                logger.info(f"Successfully connected to ntfy topic via WebSocket.")
                # Pass the session to handle_messages
                await self.handle_messages(websocket, self.session)

            except (websockets.exceptions.ConnectionClosedError,
                    websockets.exceptions.ConnectionClosedOK) as e:
                logger.warning(f"WebSocket connection closed: {e}. Reconnecting in {self.reconnect_delay}s...")
            except websockets.exceptions.InvalidURI:
                logger.critical(f"Invalid WebSocket URI: {self.websocket_url}. Receiver stopping.")
                self.enabled = False # Stop trying on fatal config error
            except (ConnectionRefusedError, OSError, socket.gaierror) as e:
                 logger.error(f"WebSocket connection failed (Network/Socket Error): {e}. Retrying in {self.reconnect_delay}s...")
            except (TimeoutError, asyncio.TimeoutError) as e: # Catch generic TimeoutError and asyncio.TimeoutError
                 logger.error(f"WebSocket connection attempt timed out ({connect_timeout}s). Retrying in {self.reconnect_delay}s...")
            except asyncio.CancelledError:
                logger.info("Receiver task cancelled during shutdown.")
                self.enabled = False # Ensure loop terminates on cancellation
            except Exception as e:
                # Catch potential proxy errors more specifically if needed
                if "python-socks" in str(e):
                     logger.critical(f"Connection error possibly related to proxy: {e}. Ensure 'python-socks' is installed if using SOCKS proxy. Retrying in {self.reconnect_delay}s...")
                else:
                    logger.critical(f"Unexpected error in WebSocket connection loop: {e}. Retrying in {self.reconnect_delay}s...", exc_info=True)
            finally:
                # Ensure websocket is closed if it was opened
                if websocket and not websocket.close:
                     await websocket.close()
                     logger.debug("WebSocket connection closed in finally block.")


            # Wait before reconnecting, only if enabled and not cancelled
            if self.enabled:
                try:
                    await asyncio.sleep(self.reconnect_delay)
                except asyncio.CancelledError:
                     logger.info("Receiver reconnect sleep interrupted by cancellation.")
                     self.enabled = False # Ensure loop terminates

        logger.info("Ntfy Receiver run loop finished.")


    async def handle_messages(self, websocket, session: aiohttp.ClientSession):
        """Processes incoming messages from the WebSocket."""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event = data.get('event')

                    if event == 'message':
                        # Pass the session down
                        await self.process_ntfy_message(data, session)
                    elif event == 'keepalive':
                        logger.debug("Received keepalive.")
                    elif event == 'open':
                        logger.info("WebSocket connection confirmed open by ntfy.")
                    elif event == 'poll_request':
                         logger.debug("Received poll_request signal.") # ntfy internal
                    else:
                        logger.warning(f"Received unknown event type: {event}, Data: {str(data)[:100]}...")

                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode JSON message: {message[:200]}...")
                except Exception as e:
                    # Log errors processing individual messages but continue listening
                    logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
        except asyncio.CancelledError:
             logger.info("Receiver message handling loop cancelled.")
             # Allow cancellation to propagate
             raise
        except websockets.exceptions.ConnectionClosed as e:
             logger.warning(f"WebSocket connection closed while handling messages: {e}")
             # Let the outer loop handle reconnection
        except Exception as e:
             logger.error(f"Unexpected error in handle_messages loop: {e}", exc_info=True)
             # Depending on severity, might want to raise or let outer loop retry


    async def process_ntfy_message(self, data: Dict[str, Any], session: aiohttp.ClientSession):
        """Processes a single ntfy message event, downloading attachments and updating clipboard."""
        message_id = data.get('id', 'N/A')
        message_content = data.get('message', '') # The main text content of the notification
        attachment = data.get('attachment')
        title = data.get('title', '') # Notification title

        logger.info(f"Received message (ID: {message_id}, Title: '{title[:30]}...')")

        text_to_copy: Optional[str] = None
        image_to_copy: Optional[bytes] = None
        image_filename: Optional[str] = None
        copy_source_description: str = "Unknown" # For logging

        # --- Prioritize Attachment ---
        if attachment and isinstance(attachment, dict):
            attach_url = attachment.get('url')
            attach_name = attachment.get('name')
            attach_type = attachment.get('type') # MIME type if provided
            attach_size = attachment.get('size')

            if attach_url and attach_name:
                logger.info(f"Message has attachment: '{attach_name}' (Type: {attach_type or 'N/A'}, Size: {attach_size or 'N/A'})")

                # Download the attachment content using the shared session
                download_result = await self.ntfy_client.download_attachment(session, attach_url)

                if download_result:
                    content_bytes, content_type_header = download_result
                    resolved_content_type = attach_type or content_type_header # Prefer explicit type

                    # Check if it's an image
                    if self.ntfy_client.is_image_attachment(attach_name, resolved_content_type):
                        if self.is_macos_image_support:
                            logger.info(f"Detected image attachment '{attach_name}'. Preparing to copy image (macOS).")
                            image_to_copy = content_bytes
                            image_filename = attach_name
                            copy_source_description = f"Image Attachment '{attach_name}'"
                        else:
                            logger.info(f"Detected image attachment '{attach_name}'. Copying URL (non-macOS or disabled).")
                            # Ensure URL is resolved before copying
                            resolved_url = self.ntfy_client._resolve_url(attach_url)
                            text_to_copy = resolved_url if resolved_url else attach_url # Fallback to original if resolve fails
                            copy_source_description = f"Image Attachment URL '{attach_name}'"

                    # Check if it's a text file
                    elif self.ntfy_client.is_text_attachment(attach_name, resolved_content_type):
                        logger.info(f"Detected text attachment '{attach_name}'. Decoding content.")
                        text_to_copy = self.ntfy_client.decode_text_content(content_bytes, attach_url)
                        copy_source_description = f"Text Attachment '{attach_name}'"
                        if text_to_copy is None:
                             logger.warning(f"Failed to decode text attachment '{attach_name}'. Falling back to message body.")
                             text_to_copy = message_content # Fallback
                             copy_source_description = f"Message Body (Text attach decode failed: '{attach_name}')"

                    # Unknown attachment type
                    else:
                        logger.info(f"Attachment '{attach_name}' is not a recognized image or text type. Copying message body if available.")
                        if message_content:
                            text_to_copy = message_content # Fallback to message body
                            copy_source_description = f"Message Body (Unknown attach type: '{attach_name}')"
                        else:
                            logger.warning(f"Unknown attachment type '{attach_name}' and no message body. Nothing to copy.")
                            return # Nothing to do

                else: # Download failed
                    logger.warning(f"Failed to download attachment '{attach_name}'. Falling back to message body if available.")
                    if message_content:
                        text_to_copy = message_content # Fallback
                        copy_source_description = f"Message Body (Attach download failed: '{attach_name}')"
                    else:
                        logger.warning(f"Attachment download failed for '{attach_name}' and no message body. Nothing to copy.")
                        return # Nothing to do

            else: # Attachment info incomplete
                logger.warning("Message has incomplete attachment data. Copying message body if available.")
                if message_content:
                    text_to_copy = message_content # Fallback
                    copy_source_description = "Message Body (Incomplete attach data)"
                else:
                    logger.warning("Incomplete attachment data and no message body. Nothing to copy.")
                    return # Nothing to do

        # --- No Attachment or Fallback ---
        else:
            if message_content:
                 logger.info("Received message with no attachment or fell back to message body.")
                 text_to_copy = message_content
                 copy_source_description = "Message Body"
            else:
                 logger.info("Received message with no attachment and no message body. Nothing to copy.")
                 return # Nothing to do

        # --- Perform Clipboard Action ---
        # Use run_in_executor for synchronous clipboard operations
        loop = asyncio.get_running_loop()
        copied_successfully = False

        try:
            if image_to_copy and image_filename and self.is_macos_image_support:
                logger.info(f"Attempting to copy {copy_source_description} to clipboard (macOS image)...")
                copied_successfully = await loop.run_in_executor(
                    None,
                    self.clipboard.set_image_macos,
                    image_to_copy,
                    image_filename,
                    "Receiver" # Source description for clipboard manager logs
                )
                if copied_successfully:
                     logger.info(f"Successfully copied {copy_source_description} to clipboard.")
                     # No need to set _last_received_text for images currently
                else:
                     logger.error(f"Failed to copy {copy_source_description} (image) to clipboard.")
                     # Optional: Fallback to copying text if image copy fails?

            # If we have text to copy (either primary or fallback) and image wasn't copied
            if text_to_copy is not None and not copied_successfully:
                logger.info(f"Attempting to copy {copy_source_description} to clipboard (text)...")
                copied_successfully = await loop.run_in_executor(
                    None,
                    self.clipboard.set_text,
                    text_to_copy,
                    "Receiver" # Source description
                )
                if copied_successfully:
                    # !!! IMPORTANT: Update shared state for loop prevention !!!
                    self.shared_state['_last_received_text'] = text_to_copy
                    logger.info(f"Successfully copied {copy_source_description} to clipboard. Updated _last_received_text.")
                else:
                    logger.error(f"Failed to copy {copy_source_description} (text) to clipboard.")

        except Exception as e:
             # Catch errors during the clipboard setting phase
             logger.error(f"Error during clipboard update for {copy_source_description}: {e}", exc_info=True)