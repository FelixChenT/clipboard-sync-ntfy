#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Go to the project root directory (one level up from scripts)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

echo "Project Root: $(pwd)"

# --- Configuration ---
VENV_DIR="venv" # Virtual environment directory name
PYTHON_EXEC="python3" # Command to run Python 3
REQUIREMENTS_FILE="requirements.txt"
MAIN_SCRIPT="main.py"
CONFIG_FILE="config/config.yaml"
CONFIG_EXAMPLE="config/config.yaml.example"

# --- Argument Parsing ---
# Default: do not update dependencies unless requested or first run
update_dependencies=false
SERVICE_MODE="both" # Default service mode

# Check for --update-deps first
if [[ "$1" == "--update-deps" ]]; then
  update_dependencies=true
  echo "Argument '--update-deps' provided. Will update dependencies."
  shift # Remove --update-deps from arguments
fi

# Check for service mode (sender, receiver, both)
if [[ "$1" == "sender" || "$1" == "receiver" || "$1" == "both" ]]; then
  SERVICE_MODE="$1"
  echo "Service mode specified: $SERVICE_MODE"
  shift # Remove service mode argument
else
  echo "No specific service mode (sender/receiver/both) specified, or argument is not recognized as such. Defaulting to '$SERVICE_MODE'."
  # Any remaining $1 would be passed to main.py via "$@"
fi

# --- Functions ---
check_python() {
    if ! command -v $PYTHON_EXEC &> /dev/null; then
        echo "Error: '$PYTHON_EXEC' command not found."
        echo "Please install Python 3."
        exit 1
    fi
    # Optional: Check Python version >= 3.8
    # $PYTHON_EXEC -c 'import sys; sys.exit(not (sys.version_info >= (3, 8)))'
    # if [ $? -ne 0 ]; then
    #     echo "Error: Python 3.8 or higher is required."
    #     exit 1
    # fi
}

setup_venv() {
    # This function now only *ensures* venv exists and activates it.
    # Dependency installation logic is moved outside.
    local venv_created=false
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating Python virtual environment in '$VENV_DIR'..."
        $PYTHON_EXEC -m venv "$VENV_DIR"
        if [ $? -ne 0 ]; then
            echo "Error: Failed to create virtual environment."
            exit 1
        fi
        echo "Virtual environment created."
        venv_created=true # Flag that we just created it
    else
        echo "Virtual environment '$VENV_DIR' already exists."
    fi

    echo "Activating virtual environment..."
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    if [ $? -ne 0 ]; then
        echo "Warning: Failed to activate virtual environment automatically."
        echo "Attempting to continue, but dependency issues might occur."
        echo "Try activating manually: source $VENV_DIR/bin/activate"
    fi

    # Return status indicating if venv was newly created (0 = new, 1 = existing)
    # This helps decide if initial install is needed.
    if [ "$venv_created" = true ]; then
        return 0 # Success, and venv was created
    else
        return 1 # Success, but venv existed
    fi
}

install_deps() {
    echo "Installing/updating dependencies from $REQUIREMENTS_FILE..."
    # Upgrade pip first within the venv
    pip install --upgrade pip
    # Install requirements
    pip install -r "$REQUIREMENTS_FILE"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies."
        # Consider exiting if install fails, especially on first run
        # exit 1
        echo "Continuing despite dependency installation errors..."
    fi
    echo "Dependency installation/update check complete."
}

check_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Warning: Configuration file '$CONFIG_FILE' not found."
        if [ -f "$CONFIG_EXAMPLE" ]; then
            echo "An example configuration exists at '$CONFIG_EXAMPLE'."
            echo "Please copy it to '$CONFIG_FILE' and customize it:"
            echo "cp '$CONFIG_EXAMPLE' '$CONFIG_FILE'"
            # Optionally exit if config is absolutely required
            # exit 1
        else
             echo "Error: Example configuration '$CONFIG_EXAMPLE' also missing!"
             exit 1
        fi
         echo "Attempting to run without '$CONFIG_FILE', the application might fail."
    fi
}


# --- Main Execution ---
echo "--- Clipboard Sync Ntfy Startup ---"

check_python

# Setup/Activate venv and check if it was newly created
setup_venv
venv_was_created=$? # Capture the return status: 0 if new, 1 if existing

# --- Conditionally install dependencies ---
if [ $venv_was_created -eq 0 ]; then
  # If venv was just created, ALWAYS install dependencies
  echo "Performing initial dependency installation for new virtual environment..."
  install_deps
elif [ "$update_dependencies" = true ]; then
  # If venv existed, but --update-deps flag was given
  echo "Updating dependencies as requested via --update-deps flag..."
  install_deps
else
  # If venv existed and no --update-deps flag
  echo "Skipping dependency update (default behavior)."
  # Optional: Basic check if pip exists when skipping
   if ! command -v pip &> /dev/null; then
        echo "Warning: 'pip' command not found in activated venv. Dependencies might be missing or venv activation failed."
   fi
fi

check_config

echo "Starting the application ($MAIN_SCRIPT)..."

# Use exec to replace the shell process with the Python process
# Pass remaining arguments (after potentially removing --update-deps) to the Python script
exec $PYTHON_EXEC "$PROJECT_ROOT/$MAIN_SCRIPT" --mode "$SERVICE_MODE" "$@"

# If exec fails (e.g., python not found after venv activation issues), this line will be reached.
echo "Error: Failed to execute '$PYTHON_EXEC $PROJECT_ROOT/$MAIN_SCRIPT'" >&2
exit 1