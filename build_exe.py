#!/usr/bin/env python3
"""
Build script to create the History Clipboard Manager executable using PyInstaller.

This script creates a standalone Windows executable from the source code.
The output will be in the dist/ directory.

Usage:
    python build_exe.py
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and print output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True
    )
    if result.stdout:
        print(result.stdout)
    return result


def main():
    """Main build function."""
    # Get the project root directory
    project_root = Path(__file__).parent
    src_dir = project_root / "src"

    print("=" * 60)
    print("History Clipboard Manager - Build Script")
    print("=" * 60)
    print()

    # Check if src directory exists
    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}")
        sys.exit(1)

    # Change to src directory (PyInstaller needs to run from there)
    os.chdir(src_dir)
    print(f"Working directory: {os.getcwd()}")
    print()

    # Clean previous builds
    print("Cleaning previous builds...")
    for dir_name in ["build", "dist"]:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"  Removed {dir_name}/")
    print()

    # Run PyInstaller
    print("Building executable with PyInstaller...")
    print("-" * 60)

    try:
        run_command([
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "build.spec"
        ])
    except subprocess.CalledProcessError as e:
        print()
        print("Error: PyInstaller build failed!")
        print(f"Return code: {e.returncode}")
        if e.stderr:
            print(f"Error output:\n{e.stderr}")
        sys.exit(1)

    print()
    print("-" * 60)
    print("Build completed successfully!")
    print()

    # Find the generated executable
    exe_files = list(Path("dist").glob("*.exe"))
    if exe_files:
        exe_path = exe_files[0]
        file_size = exe_path.stat().st_size / (1024 * 1024)  # Size in MB

        print(f"Executable created: {exe_path}")
        print(f"File size: {file_size:.2f} MB")
        print()

        # Absolute path for easy copying
        abs_path = exe_path.resolve()
        print(f"Full path: {abs_path}")
        print()
        print("You can now:")
        print(f"  1. Copy the executable to another PC")
        print(f"  2. Run it directly from: {abs_path}")
    else:
        print("Warning: No executable found in dist/ directory")
        sys.exit(1)

    print()
    print("=" * 60)
    print("Build process complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
