# Build Instructions

## Creating the Executable

To build the History Clipboard Manager executable:

```bash
python build_exe.py
```

Or using UV:

```bash
uv run python build_exe.py
```

The build script will:
1. Clean previous build artifacts
2. Run PyInstaller with the configuration in `src/build.spec`
3. Create a standalone executable in `src/dist/history_clipboard_manager.exe`

## Output

The executable will be created at:
```
src/dist/history_clipboard_manager.exe
```

File size is approximately 20-21 MB.

## Build Artifacts

The following directories are created during the build but are **not** tracked by git:
- `src/build/` - PyInstaller build files
- `src/dist/` - Final executable output

## Requirements

The build script requires all project dependencies to be installed. With UV:
```bash
uv sync
```

Or manually:
```bash
pip install -r src/requirements.txt
```

## Customizing the Build

To modify the build configuration, edit `src/build.spec`.

Key settings:
- `--onefile` - Creates a single executable file
- `--windowed` - No console window
- Icon files are bundled from `src/icons/*.png`
