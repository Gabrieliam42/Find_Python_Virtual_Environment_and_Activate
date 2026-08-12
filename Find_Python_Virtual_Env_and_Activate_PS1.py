# Script Developer: Gabriel Mihai Sandu
# GitHub Profile: https://github.com/Gabrieliam42

import os
import sys
import subprocess
import platform
import ctypes
import shutil
import stat

PREFERRED_WINDOWS_VENV_NAMES = (
    ".venv312",
    ".venv313",
    ".venv314",
    ".venv311",
    ".venv310",
)
EXCLUDED_WINDOWS_SEARCH_DIR_NAMES = {
    ".cache",
    ".git",
    ".hg",
    ".svn",
    ".tmp",
    "__pycache__",
    "backup",
    "build",
    "dist",
    "node_modules",
    "tmp",
}
EXCLUDED_WINDOWS_SEARCH_DIR_PREFIXES = (".tmp_", "tmp_")


def should_skip_windows_search_directory(name):
    normalized = name.casefold()
    return normalized in EXCLUDED_WINDOWS_SEARCH_DIR_NAMES or normalized.startswith(
        EXCLUDED_WINDOWS_SEARCH_DIR_PREFIXES
    )


def is_wsl_virtualenv_root(path):
    return (
        os.path.isfile(os.path.join(path, "pyvenv.cfg"))
        and os.path.isfile(os.path.join(path, "bin", "activate"))
        and not os.path.isdir(os.path.join(path, "Scripts"))
    )


def find_venv_root(cwd, scripts_dir, activation_filename):
    is_windows = platform.system() == "Windows"
    if is_windows:
        for preferred_name in PREFERRED_WINDOWS_VENV_NAMES:
            preferred_root = os.path.join(cwd, preferred_name)
            preferred_scripts = os.path.join(preferred_root, "Scripts")
            if os.path.isfile(os.path.join(preferred_root, "pyvenv.cfg")) and os.path.isfile(
                os.path.join(preferred_scripts, activation_filename)
            ):
                return preferred_root

    def ignore_walk_error(_error):
        return None

    for root, dirs, files in os.walk(
        cwd,
        topdown=True,
        onerror=ignore_walk_error,
    ):
        if is_windows:
            dirs[:] = sorted(
                directory
                for directory in dirs
                if not should_skip_windows_search_directory(directory)
                and not is_wsl_virtualenv_root(os.path.join(root, directory))
            )
            if "pyvenv.cfg" not in files:
                continue

        if scripts_dir not in dirs:
            continue

        activation_path = os.path.join(root, scripts_dir, activation_filename)
        if os.path.isfile(activation_path):
            return root

    return None


def is_user_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv + ["--as-admin"]), None, 1
        )
        return True
    except:
        return False

def clean_broken_distributions(venv_root):
    site_packages = os.path.join(
        venv_root, "Lib", "site-packages"
    ) if platform.system() == "Windows" else os.path.join(
        venv_root, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"
    )

    if os.path.isdir(site_packages):
        for entry in os.listdir(site_packages):
            if entry.startswith("~"):
                path = os.path.join(site_packages, entry)
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                        print(f"Deleted broken directory: {path}")
                    else:
                        os.remove(path)
                        print(f"Deleted broken file: {path}")
                except Exception as e:
                    print(f"Failed to delete {path}: {e}")

def make_pip_writable(site_packages):
    for entry in os.listdir(site_packages):
        if entry.lower().startswith("pip-") and (entry.endswith(".dist-info") or os.path.isdir(os.path.join(site_packages, entry))):
            pip_path = os.path.join(site_packages, entry)
            for root, dirs, files in os.walk(pip_path):
                for name in files:
                    fpath = os.path.join(root, name)
                    try:
                        os.chmod(fpath, stat.S_IWRITE | stat.S_IREAD)
                    except Exception as e:
                        print(f"Could not change permissions on {fpath}: {e}")

def upgrade_pip(scripts_path, site_packages):
    make_pip_writable(site_packages)

    python_exe = os.path.join(scripts_path, "python.exe")
    base_cmd = [python_exe, "-m", "pip", "install", "--upgrade", "pip"]
    force_cmd = [python_exe, "-m", "pip", "install", "--upgrade", "--force-reinstall", "pip"]
    ensure_cmd = [python_exe, "-m", "ensurepip", "--upgrade"]

    try:
        print("Trying normal pip upgrade...")
        result = subprocess.run(base_cmd)
        if result.returncode == 0:
            return
        print("Normal upgrade failed. Trying --force-reinstall...")
        result = subprocess.run(force_cmd)
        if result.returncode == 0:
            return
        print("Force-reinstall failed. Trying ensurepip --upgrade...")
        subprocess.run(ensure_cmd)
    except Exception as e:
        print(f"All pip upgrade attempts failed: {e}")

def find_and_activate_venv():
    cwd = os.getcwd()
    scripts_dir = 'Scripts' if platform.system() == 'Windows' else 'bin'
    activation_filename = 'Activate.ps1' if platform.system() == 'Windows' else 'activate'
    root = find_venv_root(cwd, scripts_dir, activation_filename)
    if root is None:
        print("No virtual environment found.")
        return

    scripts_path = os.path.join(root, scripts_dir)
    print(f"Virtual environment found and activated at: {root}")

    if is_user_admin():
        clean_broken_distributions(root)

    site_packages = os.path.join(
        root, "Lib", "site-packages"
    ) if platform.system() == "Windows" else os.path.join(
        root, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"
    )

    if platform.system() == 'Windows':
        upgrade_pip(scripts_path, site_packages)
        activate_script = os.path.join(scripts_path, "Activate.ps1")
        activate_command = ["powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", activate_script]
    else:
        activate_command = f'source "{os.path.join(scripts_path, "activate")}"'

    subprocess.run(
        activate_command,
        shell=False if platform.system() == 'Windows' else True,
        executable='/bin/bash' if platform.system() != 'Windows' else None
    )

if __name__ == "__main__":
    if platform.system() == "Windows":
        if "--as-admin" not in sys.argv:
            if not is_user_admin():
                print("Not running as admin. Attempting to relaunch with elevated privileges...")
                if run_as_admin():
                    sys.exit(0)
                else:
                    print("Failed to relaunch as admin. Continuing without admin rights...")
    find_and_activate_venv()
