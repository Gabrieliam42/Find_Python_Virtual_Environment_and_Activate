# Script Developer: Gabriel Mihai Sandu
# GitHub Profile: https://github.com/Gabrieliam42

import os
import shlex
import subprocess
import sys

DISTRO_NAME = "Ubuntu"


def is_wsl():
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False


def pause_and_exit(message, code=1):
    print(message)
    try:
        input("Press Enter to exit...")
    except EOFError:
        pass
    sys.exit(code)


def find_activate_paths():
    cwd = os.getcwd()
    activate_paths = []
    for root, dirs, files in os.walk(cwd):
        dirs.sort()
        if "bin" in dirs:
            activate_path = os.path.join(root, "bin", "activate")
            if os.path.isfile(activate_path):
                activate_paths.append(activate_path)
    return sorted(activate_paths)


def select_activate_path(activate_paths):
    if len(activate_paths) == 1:
        return activate_paths[0]

    print("Virtual environments found in the current directory tree:")
    for index, activate_path in enumerate(activate_paths, start=1):
        print(f"{index}. {activate_path}")

    while True:
        user_choice = input("Select the number of the virtual environment you want to activate: ").strip()
        if user_choice.isdigit():
            choice = int(user_choice)
            if 1 <= choice <= len(activate_paths):
                return activate_paths[choice - 1]
        print(f"Invalid selection. Enter a number between 1 and {len(activate_paths)}.")


def drop_to_bash_with_activation(activate_path):
    bash_command = (
        f'ACTIVATE_PATH={shlex.quote(activate_path)}; '
        'source "$ACTIVATE_PATH"; '
        'venv_prompt_fix=\'if [ -n "$VIRTUAL_ENV" ]; then _venv_name="$(basename "$VIRTUAL_ENV")"; '
        'case "$PS1" in ("($_venv_name) "*) ;; (*) PS1="($_venv_name) $PS1" ;; esac; fi\'; '
        'if [ -n "${PROMPT_COMMAND:-}" ]; then '
        'export PROMPT_COMMAND="$venv_prompt_fix; $PROMPT_COMMAND"; '
        'else '
        'export PROMPT_COMMAND="$venv_prompt_fix"; '
        'fi; '
        'echo "Activated virtual environment from: $ACTIVATE_PATH"; '
        'exec bash -i'
    )
    result = subprocess.run(["bash", "-lc", bash_command])
    if result.returncode != 0:
        pause_and_exit("Failed to activate the selected virtual environment.")


def activate_virtualenv_wsl():
    activate_paths = find_activate_paths()
    if not activate_paths:
        pause_and_exit(
            "No virtual environment activation script found in the current directory or its subdirectories."
        )

    activate_path = select_activate_path(activate_paths)
    drop_to_bash_with_activation(activate_path)


def ensure_wsl_available():
    try:
        subprocess.run(
            ["wsl", "-d", DISTRO_NAME, "-e", "bash", "-lc", "exit 0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        pause_and_exit("WSL command not found. Ensure WSL is installed and available in PATH.")
    except subprocess.CalledProcessError as exc:
        error_text = (exc.stderr or "").strip()
        if error_text:
            pause_and_exit(
                f"Unable to run 'wsl -d {DISTRO_NAME}'. Ensure the distro exists and WSL is working.\n{error_text}"
            )
        pause_and_exit(f"Unable to run 'wsl -d {DISTRO_NAME}'. Ensure the distro exists and WSL is working.")


def convert_windows_cwd_to_wsl():
    windows_cwd = os.getcwd()
    result = subprocess.run(
        ["wsl", "-d", DISTRO_NAME, "-e", "wslpath", "-a", "-u", windows_cwd],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        error_text = result.stderr.strip() or "Unknown error while converting Windows path to WSL path."
        pause_and_exit(f"Failed to convert current directory to WSL path: {error_text}")

    wsl_cwd = result.stdout.strip()
    if not wsl_cwd:
        pause_and_exit("Failed to convert current directory to WSL path: empty result.")
    return wsl_cwd


def activate_virtualenv_from_windows():
    ensure_wsl_available()
    wsl_cwd = convert_windows_cwd_to_wsl()

    bash_script = f"""
set -e
cd -- {shlex.quote(wsl_cwd)}
mapfile -t activate_paths < <(find . -type f -path "*/bin/activate" | sort)
if [ "${{#activate_paths[@]}}" -eq 0 ]; then
    echo "No virtual environment activation script found in the current directory or its subdirectories."
    echo "Press Enter to exit..."
    read -r _
    exit 1
fi
if [ "${{#activate_paths[@]}}" -eq 1 ]; then
    selected_activate="${{activate_paths[0]}}"
else
    echo "Virtual environments found in the current directory tree:"
    for i in "${{!activate_paths[@]}}"; do
        printf "%d. %s\\n" "$((i + 1))" "${{activate_paths[$i]}}"
    done
    while true; do
        read -rp "Select the number of the virtual environment you want to activate: " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${{#activate_paths[@]}} )); then
            break
        fi
        echo "Invalid selection. Enter a number between 1 and ${{#activate_paths[@]}}."
    done
    selected_activate="${{activate_paths[$((choice - 1))]}}"
fi
source "$selected_activate"
venv_prompt_fix='if [ -n "$VIRTUAL_ENV" ]; then _venv_name="$(basename "$VIRTUAL_ENV")"; case "$PS1" in ("($_venv_name) "*) ;; (*) PS1="($_venv_name) $PS1" ;; esac; fi'
if [ -n "${{PROMPT_COMMAND:-}}" ]; then
    export PROMPT_COMMAND="$venv_prompt_fix; $PROMPT_COMMAND"
else
    export PROMPT_COMMAND="$venv_prompt_fix"
fi
echo "Activated virtual environment from: $selected_activate"
exec bash -i
"""

    result = subprocess.run(["wsl", "-d", DISTRO_NAME, "-e", "bash", "-lc", bash_script])
    if result.returncode != 0:
        pause_and_exit("Failed to start WSL shell and activate virtual environment.")


if __name__ == "__main__":
    if is_wsl():
        activate_virtualenv_wsl()
    else:
        activate_virtualenv_from_windows()
