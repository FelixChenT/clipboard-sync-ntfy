#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse # Added for command-line argument parsing
import asyncio
import logging
import sys
import signal
import aiohttp # Import aiohttp
from typing import Dict

# --- Project Imports ---
from clipboard_sync.config import load_config
from clipboard_sync.utils import setup_logging, check_pyobjc
from clipboard_sync.clipboard_manager import ClipboardManager
from clipboard_sync.ntfy_client import NtfyClient
from clipboard_sync.sender import ClipboardSender
from clipboard_sync.receiver import NtfyReceiver

# --- Global Logger ---
# Setup basic logging first to catch early errors, will be reconfigured by config
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
logger = logging.getLogger("Main")

# --- Shared State ---
# Used to prevent the sender from immediately re-sending content just received.
shared_state: Dict[str, any] = {
    "_last_received_text": None,
}

# --- Signal Handling ---
shutdown_event = asyncio.Event()

def handle_signal(sig, frame):
    """Sets the shutdown event when SIGINT or SIGTERM is received."""
    if not shutdown_event.is_set():
        logger.warning(f"Received signal {signal.Signals(sig).name}. Initiating graceful shutdown...")
        shutdown_event.set()
    else:
        logger.warning("Shutdown already in progress.")

async def main():
    """Main function to load config, set up components, run tasks, and handle shutdown."""

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Clipboard Sync with Ntfy")
    parser.add_argument(
        "--mode",
        type=str,
        choices=['sender', 'receiver', 'both'],
        default=None, # Default is None, meaning rely on config file
        help="Specify the operating mode: 'sender', 'receiver', or 'both'. Overrides config.yaml."
    )
    args = parser.parse_args()

    # --- Load Configuration ---
    config = load_config()
    if not config:
        logger.critical("Failed to load configuration. Exiting.")
        sys.exit(1)

    # --- Setup Logging based on Config (initial setup) ---
    log_config = config.get('logging', {})
    setup_logging(log_config.get('level', 'INFO'))
    logger.info("Logging configured.")

    # --- Apply Command-Line Mode Override ---
    if args.mode:
        if args.mode == "sender":
            logger.info("Overriding config: Starting SENDER only based on --mode argument.")
            config.setdefault('sender', {})['enabled'] = True
            config.setdefault('receiver', {})['enabled'] = False
        elif args.mode == "receiver":
            logger.info("Overriding config: Starting RECEIVER only based on --mode argument.")
            config.setdefault('sender', {})['enabled'] = False
            config.setdefault('receiver', {})['enabled'] = True
        elif args.mode == "both":
            logger.info("Overriding config: Starting BOTH sender and receiver based on --mode argument.")
            config.setdefault('sender', {})['enabled'] = True
            config.setdefault('receiver', {})['enabled'] = True
    else:
        logger.info("Using config file settings for enabling sender/receiver (no --mode override).")
    
    # Ensure 'enabled' keys exist even if not overridden, defaulting to what's in config or False
    # This is important for the Sender/Receiver class initializers
    config.setdefault('sender', {}).setdefault('enabled', False)
    config.setdefault('receiver', {}).setdefault('enabled', False)


    # --- Platform Checks ---
    is_macos = sys.platform == 'darwin'
    pyobjc_available = check_pyobjc() # Checks and logs availability
    macos_cfg = config.get('macos', {})
    macos_image_support = is_macos and pyobjc_available and macos_cfg.get('image_support', False)
    if is_macos and not macos_image_support:
         logger.warning("Running on macOS, but image support is disabled (PyObjC missing or config setting).")
    elif not is_macos:
         logger.info("Running on non-macOS platform. Image clipboard operations will be skipped by receiver.")

    # --- Create shared aiohttp ClientSession ---
    # Use async with for proper session management (creation and closing)
    async with aiohttp.ClientSession() as session:
        logger.info("Shared aiohttp ClientSession created.")
        sender = None
        receiver = None
        tasks = []

        try:
            # --- Initialize Components (pass session) ---
            clipboard_manager = ClipboardManager(macos_cfg)
            ntfy_client = NtfyClient(config) # NtfyClient itself doesn't store the session
            # Pass session to Sender and Receiver during initialization
            sender = ClipboardSender(config, clipboard_manager, ntfy_client, shared_state, session)
            receiver = NtfyReceiver(config, clipboard_manager, ntfy_client, shared_state, session)

            # --- Create Tasks ---
            if sender.enabled:
                sender_task = asyncio.create_task(sender.run(), name="Sender")
                tasks.append(sender_task)
                logger.info("Sender task created.")
            else:
                logger.info("Sender is disabled. Task not created.")

            if receiver.enabled:
                receiver_task = asyncio.create_task(receiver.run(), name="Receiver")
                tasks.append(receiver_task)
                logger.info("Receiver task created.")
            else:
                logger.info("Receiver is disabled. Task not created.")

            if not tasks:
                logger.warning("Both sender and receiver are disabled. Nothing to do. Exiting.")
                # Session closed automatically by 'async with'
                return # Exit main coroutine early

            logger.info("Application started. Press Ctrl+C to stop.")

            # --- Wait for tasks or shutdown signal ---
            shutdown_task = asyncio.create_task(shutdown_event.wait(), name="ShutdownWatcher")
            # Add the shutdown watcher task to the list we wait on
            all_tasks_to_wait = tasks + [shutdown_task]

            # Wait for the first task to complete (either a main task or the shutdown signal)
            done, pending = await asyncio.wait(
                all_tasks_to_wait,
                return_when=asyncio.FIRST_COMPLETED
            )

            # --- Shutdown Logic ---
            logger.info("Shutdown initiated or a task finished unexpectedly.")

            # Check which task(s) completed
            for task in done:
                task_name = task.get_name()
                if task is shutdown_task:
                    logger.info("Shutdown triggered by signal.")
                else:
                    # A main task finished, log its result or exception
                    try:
                        result = task.result() # Check for exceptions
                        logger.warning(f"Task '{task_name}' finished unexpectedly with result: {result}")
                    except asyncio.CancelledError:
                         # This can happen if shutdown signal arrives *just* as task finishes
                         logger.info(f"Task '{task_name}' was cancelled (likely during shutdown).")
                    except Exception as e:
                        logger.error(f"Task '{task_name}' finished unexpectedly with an error:", exc_info=e)

            logger.info("Cancelling pending tasks...")
            cancelled_tasks = []
            for task in pending:
                 task_name = task.get_name()
                 logger.debug(f"Cancelling task '{task_name}'...")
                 task.cancel()
                 cancelled_tasks.append(task)

            # Wait for the cancelled tasks to actually finish handling the cancellation
            if cancelled_tasks:
                logger.debug(f"Waiting for {len(cancelled_tasks)} cancelled tasks to finish...")
                # Wait with a timeout
                _, still_pending = await asyncio.wait(cancelled_tasks, timeout=10.0)
                if still_pending:
                    logger.warning(f"{len(still_pending)} tasks did not finish cancelling within timeout.")
                else:
                    logger.debug("All cancelled tasks finished.")
            else:
                 logger.debug("No pending tasks needed cancellation.")

        except Exception as e:
            # Catch errors during initialization or the main wait loop
            logger.critical(f"Critical error in main execution block: {e}", exc_info=True)
            # Ensure tasks are cancelled even if error happens before shutdown logic
            for task in tasks:
                 if not task.done():
                     task.cancel()
            if 'shutdown_task' in locals() and not shutdown_task.done():
                 shutdown_task.cancel()
            # Re-raise the exception after attempting cleanup
            raise
        finally:
            # This block runs whether main completes normally or via exception
            # The 'async with session:' ensures session.close() is called here
            logger.info("aiohttp ClientSession is being closed by 'async with'.")

    # --- End of async with session block ---
    logger.info("Main coroutine finished.")


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    # Do this *before* starting the event loop
    signal.signal(signal.SIGINT, handle_signal)  # Ctrl+C
    signal.signal(signal.SIGTERM, handle_signal) # Termination signal

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # This might still happen if signal handler setup fails or during interpreter shutdown
        logger.info("KeyboardInterrupt caught directly in __main__. Forcing exit.")
        # No graceful shutdown possible here usually
    except Exception as e:
        # Catch any unexpected errors from asyncio.run(main()) itself
        logger.critical(f"Unhandled exception during asyncio.run(main): {e}", exc_info=True)
        sys.exit(1) # Exit with error code
    finally:
        # This block executes after the event loop has completely stopped
        logger.info("Application finished.")
        # Explicitly flush logs if using file handlers, etc.
        logging.shutdown()