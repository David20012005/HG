#!/usr/bin/env python3
"""
Automated installer for Honeygain on Linux.
Uses subprocess to run system commands.
Ensures Honeygain starts at every system boot via systemd.
"""

import subprocess
import sys
import os
import argparse
import time


def check_root():
    """Exit if not running as root."""
    if os.geteuid() != 0:
        print("This script must be run as root (use sudo).", file=sys.stderr)
        sys.exit(1)


def command_exists(cmd):
    """Check if a command is available in PATH."""
    return subprocess.run(
        ["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode == 0


def run_cmd(cmd, check=True, capture=False):
    """Run a shell command, optionally capturing output."""
    print(f"Running: {cmd}")
    if capture:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
    else:
        subprocess.run(cmd, shell=True, check=check)


def install_honeygain():
    """Download and run the official Honeygain installation script."""
    # Choose downloader
    if command_exists("curl"):
        downloader = "curl -s"
    elif command_exists("wget"):
        downloader = "wget -qO-"
    else:
        print("Error: Neither curl nor wget is installed. Please install one.", file=sys.stderr)
        sys.exit(1)

    install_url = "https://get.honeygain.io/linux"
    cmd = f"{downloader} {install_url} | bash"
    try:
        run_cmd(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Installation failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(1)


def setup_credentials(email, password):
    """Run honeygain once to save credentials."""
    if email and password:
        print("Setting Honeygain credentials...")
        try:
            run_cmd(f"honeygain -email {email} -pass {password}")
        except subprocess.CalledProcessError:
            print("Warning: Failed to set credentials. You may need to run 'honeygain -email ... -pass ...' manually.")
            # Continue anyway


def create_systemd_service():
    """Create a systemd service unit for honeygain and enable it."""
    service_content = """[Unit]
Description=Honeygain
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/honeygain
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
"""
    service_path = "/etc/systemd/system/honeygain.service"
    print("Creating systemd service...")
    with open(service_path, "w") as f:
        f.write(service_content)

    # Reload systemd, enable and start the service
    run_cmd("systemctl daemon-reload")
    run_cmd("systemctl enable honeygain.service")
    run_cmd("systemctl start honeygain.service")
    print("Honeygain service enabled and started.")


def main():
    parser = argparse.ArgumentParser(
        description="Install Honeygain and set up autostart via systemd."
    )
    parser.add_argument(
        "-e", "--email", help="Honeygain account email (optional, will be used to set credentials)"
    )
    parser.add_argument(
        "-p", "--password", help="Honeygain account password (optional, required if email is given)"
    )
    args = parser.parse_args()

    # Validate credentials
    if args.email and not args.password:
        print("Error: Password must be provided when using --email.", file=sys.stderr)
        sys.exit(1)
    if args.password and not args.email:
        print("Error: Email must be provided when using --password.", file=sys.stderr)
        sys.exit(1)

    check_root()

    # Check for systemd
    if not os.path.exists("/run/systemd/system"):
        print("Error: systemd not found. This script only supports systemd-based systems.", file=sys.stderr)
        sys.exit(1)

    print("Installing Honeygain...")
    install_honeygain()

    # Verify installation
    if not command_exists("honeygain"):
        print("Error: honeygain command not found after installation.", file=sys.stderr)
        sys.exit(1)

    # Set credentials if provided
    setup_credentials(args.email, args.password)

    # Create and enable systemd service
    create_systemd_service()

    print("\nInstallation completed successfully!")
    print("You can check the status with: systemctl status honeygain")


if __name__ == "__main__":
    main()
