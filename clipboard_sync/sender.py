# -*- coding: utf-8 -*-
import asyncio
import time
import logging
import aiohttp # Import aiohttp
from typing import Dict, Any, Optional

from .clipboard_manager import ClipboardManager
from .ntfy_client import NtfyClient

logger = logging.getLogger("Sender")

class ClipboardSender:
    """Monitors the local clipboard and sends new text content to ntfy."""

    # Modify __init__ to accept and store the session
    def __init__(self, config: Dict[str, Any], clipboard_manager: ClipboardManager, ntfy_client: NtfyClient, shared_state: Dict, session: aiohttp.ClientSession):
        self.config = config.get('sender', {})
        self.clipboard = clipboard_manager
        self.ntfy_client = ntfy_client
        self.shared_state = shared_state
        self.session = session # Store the session

        self.enabled = self.config.get('enabled', False)
        self.poll_interval = float(self.config.get('poll_interval_seconds', 1.0))
        self.last_posted_text: Optional[str] = None

        if not self.enabled:
            logger.info("Clipboard Sender is disabled in the configuration.")
        elif not self.config.get('ntfy_topic_url'):
            logger.error("Sender is enabled but ntfy_topic_url is not configured. Disabling sender.")
            self.enabled = False
        # Check if session was provided
        elif not self.session:
             logger.error("Sender requires an aiohttp ClientSession but none was provided. Disabling sender.")
             self.enabled = False
        else:
             logger.info(f"Clipboard Sender initialized. Polling interval: {self.poll_interval}s")


    async def run(self):
        """Starts the monitoring loop."""
        if not self.enabled:
            return

        logger.info("Starting clipboard monitoring loop (Sender)...")
        while True:
            await self.check_and_send()
            # Handle potential CancelledError during sleep
            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                logger.info("Sender sleep interrupted by cancellation.")
                break # Exit loop on cancellation


    async def check_and_send(self):
        """
        Checks the clipboard and sends content if necessary.
        Uses run_in_executor for clipboard access.
        Uses aiohttp session for posting.
        """
        try:
            current_loop = asyncio.get_running_loop()

            # Clipboard checks still run in executor
            changed = await current_loop.run_in_executor(None, self.clipboard.has_changed)
            if not changed:
                 return

            current_text = await current_loop.run_in_executor(None, self.clipboard.get_text)
            await current_loop.run_in_executor(None, self.clipboard.update_last_change_count)

            if not current_text:
                return

            if current_text == self.last_posted_text:
                return

            last_received = self.shared_state.get('_last_received_text')
            if current_text == last_received:
                logger.info("Clipboard content matches the last received content. Skipping send to prevent loop.")
                return

            logger.info("Detected new clipboard text, preparing to send...")

            # --- Use the stored session to call the async post_text_as_file ---
            success = await self.ntfy_client.post_text_as_file(self.session, current_text)

            if success:
                logger.info("Successfully sent new clipboard text to ntfy.")
                self.last_posted_text = current_text
                self.shared_state['_last_received_text'] = None
            else:
                logger.warning("Failed to send clipboard text to ntfy.")

        # Add explicit CancelledError handling here too
        except asyncio.CancelledError:
            logger.info("Sender check_and_send cancelled.")
            # Re-raise or handle as needed, maybe just pass to let the loop break
            raise # Re-raise so the run() method's break works correctly
        except Exception as e:
            if isinstance(e, RuntimeError) and "attached to a different loop" in str(e):
                 logger.critical(f"Persistent loop mismatch error: {e}", exc_info=True)
            else:
                 logger.error(f"Error in clipboard monitoring loop: {e}", exc_info=True)
            try:
                await asyncio.sleep(min(self.poll_interval * 2, 10))
            except asyncio.CancelledError:
                 logger.info("Sender error sleep interrupted by cancellation.")
                 # Exit immediately if cancelled during error sleep
                 # Re-raising ensures the run loop breaks
                 raise