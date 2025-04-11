# -*- coding: utf-8 -*-
import sys
import logging
import subprocess
import tempfile
import os
import time
from typing import Optional, Tuple, Any

logger = logging.getLogger("ClipboardManager")

# --- macOS Specific Imports ---
try:
    if sys.platform == 'darwin':
        from AppKit import NSPasteboard, NSStringPboardType, NSPasteboardItem, NSData, NSURL, NSPasteboardTypeFileURL, NSPasteboardTypePNG, NSPasteboardTypeTIFF
        import AppKit # 确保 AppKit 被导入
        HAS_PYOBJC = True
    else:
        HAS_PYOBJC = False
except ImportError:
    HAS_PYOBJC = False

# --- Fallback/Cross-platform Text Clipboard ---
try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False
    if not HAS_PYOBJC: # Only critical if no other clipboard mechanism exists
        logger.warning("Pyperclip not found. Text clipboard functionality might be limited on non-macOS.")


class ClipboardManager:
    """
    Manages clipboard interactions, prioritizing macOS native methods
    and falling back to pyperclip for text if necessary.
    """
    def __init__(self, macos_config: Optional[dict] = None):
        self.is_macos = sys.platform == 'darwin' and HAS_PYOBJC
        self.macos_config = macos_config or {}
        self.image_support_enabled = self.is_macos and self.macos_config.get('image_support', False)
        self.image_uti_map = self.macos_config.get('image_uti_map', {}) if self.image_support_enabled else {}
        self.last_change_count = -1
        self.pasteboard = None

        if self.is_macos:
            try:
                self.pasteboard = NSPasteboard.generalPasteboard()
                self.last_change_count = self.pasteboard.changeCount()
                logger.info("Initialized macOS NSPasteboard.")
            except Exception as e:
                logger.error(f"Failed to initialize NSPasteboard: {e}. Disabling native macOS support.", exc_info=True)
                self.is_macos = False # Fallback if init fails
                self.image_support_enabled = False
        elif not HAS_PYPERCLIP:
             logger.warning("No suitable clipboard library found (PyObjC for macOS or Pyperclip). Clipboard operations will likely fail.")

    def get_change_count(self) -> int:
        """Returns the clipboard change count (macOS only)."""
        if self.is_macos and self.pasteboard:
            return self.pasteboard.changeCount()
        return int(time.time()) # Fallback: use timestamp as a crude change indicator

    def update_last_change_count(self):
        """Updates the stored change count to the current one."""
        self.last_change_count = self.get_change_count()

    def has_changed(self) -> bool:
        """Checks if the clipboard change count has increased."""
        if self.is_macos and self.pasteboard:
             current_change_count = self.pasteboard.changeCount()
             changed = current_change_count != self.last_change_count
             # self.last_change_count = current_change_count # Let caller decide when to update
             return changed
        else:
            # Non-macOS or fallback: cannot reliably detect changes this way
            # This method becomes less useful without NSPasteboard's changeCount
            logger.debug("Cannot reliably detect clipboard changes on non-macOS or without PyObjC.")
            return True # Assume changed if not on macOS with AppKit

    def get_text(self) -> Optional[str]:
        """Gets text content from the clipboard."""
        if self.is_macos and self.pasteboard:
            if NSStringPboardType in self.pasteboard.types():
                text = self.pasteboard.stringForType_(NSStringPboardType)
                # logger.debug(f"Read text from NSPasteboard (len: {len(text) if text else 0})")
                return text
            # logger.debug("NSStringPboardType not found in pasteboard types.")
            return None
        elif HAS_PYPERCLIP:
            try:
                text = pyperclip.paste()
                # logger.debug(f"Read text using pyperclip (len: {len(text) if text else 0})")
                return text
            except pyperclip.PyperclipException as e:
                logger.error(f"Error reading text with pyperclip: {e}")
                return None
        else:
            logger.warning("No method available to get clipboard text.")
            return None

    def set_text(self, text: str, source: str = "Receiver") -> bool:
        """Sets text content to the clipboard."""
        if text is None:
            logger.warning(f"Attempted to set None text to clipboard from {source}.")
            return False

        success = False
        if self.is_macos and self.pasteboard:
            try:
                self.pasteboard.clearContents()
                success = self.pasteboard.setString_forType_(text, NSStringPboardType)
                if success:
                    self.update_last_change_count() # Update count after successful write
                    logger.info(f"Text (len: {len(text)}) set to NSPasteboard by {source}.")
                else:
                    logger.error(f"NSPasteboard setString_forType_ failed for {source}.")
            except Exception as e:
                logger.error(f"Error setting text to NSPasteboard: {e}", exc_info=True)
                success = False # Ensure success is False on exception

        # Fallback or if macOS failed
        if not success and HAS_PYPERCLIP:
            try:
                pyperclip.copy(text)
                logger.info(f"Text (len: {len(text)}) set using pyperclip by {source} (macOS fallback or non-macOS).")
                success = True
                # Cannot reliably update change count here
            except pyperclip.PyperclipException as e:
                logger.error(f"Error setting text with pyperclip: {e}")
                success = False
            except Exception as e: # Catch potential weirdness like TTY issues
                logger.error(f"Unexpected error setting text with pyperclip: {e}", exc_info=True)
                success = False

        if not success:
             logger.error(f"Failed to set clipboard text from {source} using any available method.")

        return success

    def set_image_macos(self, image_data: bytes, filename: str, source: str = "Receiver") -> bool:
        """Sets image data to the clipboard (macOS only, using osascript)."""
        if not self.is_macos or not self.image_support_enabled:
            logger.warning(f"Image setting skipped: Not on macOS, PyObjC missing, or image support disabled.")
            return False
        if not image_data or not filename:
            logger.warning(f"Attempted to set empty image data or missing filename from {source}.")
            return False

        temp_path = None
        success = False
        try:
            file_ext = os.path.splitext(filename)[1].lower()
            if not file_ext:
                file_ext = '.png' # Default assumption
                logger.warning(f"Image filename '{filename}' has no extension, assuming {file_ext}.")

            # Use NamedTemporaryFile to handle cleanup better
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False, mode='wb') as temp_image_file:
                temp_path = temp_image_file.name
                temp_image_file.write(image_data)
                logger.debug(f"Image data (size: {len(image_data)}) written to temporary file: {temp_path} by {source}")

            # Using osascript as it's often more reliable for direct image pasting
            # POSIX path is crucial for osascript
            applescript_command = f'set the clipboard to (read POSIX file "{temp_path}" as picture)'
            logger.info(f"Executing AppleScript for {source}: set clipboard to (read POSIX file ... as picture)")

            process = subprocess.run(
                ['osascript', '-e', applescript_command],
                capture_output=True, text=True, check=False, timeout=10
            )

            if process.returncode == 0:
                self.update_last_change_count() # Update count after successful write
                logger.info(f"Image '{filename}' successfully set to clipboard via AppleScript by {source}.")
                success = True
            else:
                logger.error(f"AppleScript execution failed for {source} (return code: {process.returncode}).")
                if process.stdout: logger.error(f"AppleScript stdout:\n{process.stdout.strip()}")
                if process.stderr: logger.error(f"AppleScript stderr:\n{process.stderr.strip()}")

        except FileNotFoundError:
            logger.error("Cannot find 'osascript' command. Is it in the system PATH?")
        except subprocess.TimeoutExpired:
            logger.error("Executing AppleScript timed out.")
        except Exception as e:
            logger.error(f"Error setting image to clipboard via AppleScript: {e}", exc_info=True)
        finally:
            # Ensure temporary file is deleted
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.debug(f"Temporary image file deleted: {temp_path}")
                except OSError as e:
                    logger.error(f"Error deleting temporary image file {temp_path}: {e}")

        return success

    # --- Potentially add get_image() if needed, more complex with NSPasteboard ---
    # def get_image_macos(self) -> Optional[bytes]:
    #     """Gets image data from the clipboard (macOS only). More complex."""
    #     if not self.is_macos or not self.pasteboard:
    #         return None
    #     # Check for image types (e.g., NSPasteboardTypePNG, NSPasteboardTypeTIFF)
    #     # ... implementation needed ...
    #     pass
