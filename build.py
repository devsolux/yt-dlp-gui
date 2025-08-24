#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Updated Build Script for YT-DLP GUI - Video & Audio Downloader
Uses PyInstaller for packaging. On macOS this script will create a .dmg (UDZO)
from the produced .app bundle. No external packaging tools (like pkgbuild)
are required.

Usage: Run this script from the project root:
    python build.py
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

# Application information
APP_NAME = "YT-DLP-GUI"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "YT-DLP GUI - Video & Audio Downloader"

# Build configuration
BUILD_DIR = Path("build")
DIST_DIR = Path("dist")
ASSETS_DIR = Path("assets")
SRC_DIR = Path("src", "ytdlp_gui")
MAIN_SCRIPT = SRC_DIR / "main.py"


def clean_build():
    """Clean previous build artifacts"""
    print("Cleaning previous build artifacts...")
    for dir_path in [BUILD_DIR, DIST_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"   Removed {dir_path}")

    # Remove PyInstaller spec files produced previously
    for spec_file in Path(".").glob("*.spec"):
        try:
            spec_file.unlink()
            print(f"   Removed {spec_file}")
        except Exception:
            pass


def check_dependencies():
    """Check if required dependencies are installed"""
    print("Checking dependencies...")

    # (package name, import name)
    required = [
        ("PyInstaller", "PyInstaller"),
        ("customtkinter", "customtkinter"),
        ("yt-dlp", "yt_dlp"),
        ("Pillow", "PIL"),
        ("psutil", "psutil"),
    ]

    missing = []
    for pkg_name, import_name in required:
        try:
            __import__(import_name)
            print(f"   [OK] {pkg_name}")
        except ImportError:
            print(f"   [MISSING] {pkg_name} (import '{import_name}')")
            missing.append(pkg_name)

    if missing:
        print("\nMissing packages:", ", ".join(missing))
        print("Install them with: pip install -r requirements.txt")
        return False

    # On macOS we need hdiutil to create dmg (it's present on macOS by default)
    if platform.system().lower() == "darwin":
        if shutil.which("hdiutil") is None:
            print("   [WARN] 'hdiutil' not found. DMG creation will fail on macOS.")
    return True


def ensure_paths():
    """Ensure required paths exist and main script is present"""
    if not Path("src").exists():
        print("Source root 'src' not found")
        sys.exit(1)
    if not SRC_DIR.exists():
        print(f"Source package directory not found: {SRC_DIR}")
        sys.exit(1)
    if not MAIN_SCRIPT.exists():
        print(f"Main script not found: {MAIN_SCRIPT}")
        sys.exit(1)


def adjust_macos_app(app_path: Path) -> bool:
    """
    Ensure the .app bundle has executable bits for binaries and clear quarantine attributes.
    Best-effort - does not perform code signing.
    """
    print(f"Adjusting macOS app bundle: {app_path}")
    try:
        # Ensure main executables inside Contents/MacOS are executable
        macos_dir = app_path / "Contents" / "MacOS"
        if macos_dir.exists() and macos_dir.is_dir():
            for entry in macos_dir.iterdir():
                try:
                    mode = entry.stat().st_mode
                    entry.chmod(mode | 0o111)
                except Exception:
                    pass

        # Also mark helper binaries (if any) executable
        frameworks_dir = app_path / "Contents" / "Frameworks"
        if frameworks_dir.exists() and frameworks_dir.is_dir():
            for root, _, files in os.walk(frameworks_dir):
                for fname in files:
                    p = Path(root) / fname
                    try:
                        mode = p.stat().st_mode
                        p.chmod(mode | 0o111)
                    except Exception:
                        pass

        # Remove quarantine attribute if possible (so Gatekeeper won't immediately block execution)
        if shutil.which("xattr"):
            try:
                subprocess.run(["xattr", "-cr", str(app_path)], check=False)
            except Exception:
                pass

        return True
    except Exception as e:
        print("adjust_macos_app failed:", e)
        return False


def build_with_pyinstaller():
    """
    Build the application with PyInstaller.
    Produces either a .app bundle on macOS (when --windowed is used) or a folder/onefile on other platforms.
    This version ensures the src package is visible to PyInstaller via --paths, writes spec into BUILD_DIR,
    and on macOS fixes executable bits and clears quarantine attributes after build.
    """
    print("Building executable with PyInstaller...")

    system = platform.system().lower()
    is_windows = system == "windows"
    is_macos = system == "darwin"

    # Prepare common PyInstaller args
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--log-level=INFO",
    ]

    # GUI application: hide console for GUI apps
    pyinstaller_args.append("--windowed")

    # Name of the app
    pyinstaller_args += ["--name", APP_NAME]

    # Ensure spec is saved into our BUILD_DIR
    pyinstaller_args += ["--specpath", str(BUILD_DIR.resolve())]

    # Icon handling
    icon_file = None
    if ASSETS_DIR.exists():
        for ext in (".icns", ".ico", ".png"):
            candidate = ASSETS_DIR / f"icon{ext}"
            if candidate.exists():
                icon_file = candidate
                break
    if icon_file:
        pyinstaller_args += ["--icon", str(icon_file.resolve())]

    # Add data files (assets) to the bundle
    sep = ";" if is_windows else ":"
    add_data_entries = []
    if ASSETS_DIR.exists():
        add_data_entries.append(f"{str(ASSETS_DIR.resolve())}{sep}assets")

    # Instead of adding the package as data, add the parent 'src' to PyInstaller paths
    # so imports like "from ytdlp_gui import ..." work correctly.
    if SRC_DIR.exists():
        pyinstaller_args += ["--paths", str(SRC_DIR.parent.resolve())]

    # Additional individual files (README, LICENSE)
    for fname in ("README.md", "LICENSE"):
        fpath = Path(fname)
        if fpath.exists():
            add_data_entries.append(f"{str(fpath.resolve())}{sep}.")

    for item in add_data_entries:
        pyinstaller_args += ["--add-data", item]

    # Hidden imports that PyInstaller might miss
    hidden_imports = [
        "customtkinter",
        "yt_dlp",
        "PIL._tkinter_finder",
        "tkinter",
        "tkinter.ttk",
        "sqlite3",
        "json",
        "threading",
        "queue",
        "logging.handlers",
        "psutil",
    ]
    for hi in hidden_imports:
        pyinstaller_args += ["--hidden-import", hi]

    # macOS bundle identifier (helps Finder / LaunchServices)
    if is_macos:
        pyinstaller_args += ["--osx-bundle-identifier", f"org.{APP_NAME.lower()}"]

    # Entry script
    pyinstaller_args.append(str(MAIN_SCRIPT))

    print("   Running:", " ".join(pyinstaller_args))
    try:
        subprocess.run(pyinstaller_args, check=True)
        print("PyInstaller build completed successfully.")

        # Post-build: on macOS ensure executables are executable and clear quarantine attributes
        if is_macos:
            # find the .app we just built
            app_candidate = DIST_DIR / f"{APP_NAME}.app"
            if not app_candidate.exists():
                apps = list(DIST_DIR.glob("*.app"))
                app_candidate = apps[0] if apps else None

            if app_candidate and app_candidate.exists():
                try:
                    # adjust permissions and xattrs (best-effort)
                    adjust_macos_app(app_candidate)
                except Exception as e:
                    print("Warning: failed to adjust macOS .app after build:", e)

        return True
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed with exit code {e.returncode}")
        return False


def find_built_artifact():
    """
    Attempt to locate the primary built artifact in DISTRIBUTION directory.
    Returns a Path to the artifact (app dir on macOS, exe or folder on others) or None.
    """
    system = platform.system().lower()
    # Typical outputs from PyInstaller:
    # - macOS: dist/<name>.app
    # - Windows (onefile): dist/<name>.exe
    # - Windows (onedir): dist/<name>/<name>.exe
    # - Linux: dist/<name>/<name>  (executable) or dist/<name> (if onefile may be dist/<name>)
    candidates = []

    if not DIST_DIR.exists():
        return None

    # macOS .app
    if system == "darwin":
        app_path = DIST_DIR / f"{APP_NAME}.app"
        if app_path.exists():
            return app_path
        # fallback: find any .app in dist
        apps = list(DIST_DIR.glob("*.app"))
        if apps:
            return apps[0]

    # Windows executables
    if system == "windows":
        exe_direct = DIST_DIR / f"{APP_NAME}.exe"
        if exe_direct.exists():
            return exe_direct
        nested = DIST_DIR / APP_NAME / f"{APP_NAME}.exe"
        if nested.exists():
            return nested
        # fallback: first exe in dist
        for exe in DIST_DIR.rglob("*.exe"):
            return exe

    # Linux / other Unix
    # check dist/<name>/<name> or dist/<name>
    nested_exec = DIST_DIR / APP_NAME / APP_NAME
    if nested_exec.exists():
        return nested_exec
    direct = DIST_DIR / APP_NAME
    if direct.exists() and direct.is_file():
        return direct
    # fallback: any file in dist root (first match)
    for item in DIST_DIR.iterdir():
        if item.is_file():
            return item
    # deeper fallback: any file in dist/*
    for item in DIST_DIR.rglob("*"):
        if item.is_file():
            return item
    return None


def create_dmg(app_path: Path, target_dmg: Path):
    """
    Create a compressed DMG (UDZO) from the provided .app bundle or staging folder.
    Uses hdiutil on macOS.
    """
    print("Creating DMG...")

    if shutil.which("hdiutil") is None:
        print("hdiutil not found. Cannot create DMG on this system.")
        return False

    # Prepare a temporary staging directory that will be the root of the DMG
    staging = BUILD_DIR / "dmg_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    # Copy the .app bundle into staging
    try:
        if app_path.is_dir():
            # Use 'ditto' to preserve extended attributes, resource forks and symlinks (important for macOS .app bundles)
            if shutil.which("ditto"):
                subprocess.run(["ditto", str(app_path), str(staging / app_path.name)], check=True)
            else:
                # Fallback to copytree which may not preserve all macOS metadata
                shutil.copytree(app_path, staging / app_path.name)
        else:
            # if it's not a directory (rare), copy the file
            shutil.copy2(app_path, staging / app_path.name)
    except Exception as e:
        print("Failed to copy app to staging:", e)
        return False

    # Copy README/LICENSE if present
    for fname in ("README.md", "LICENSE"):
        src = Path(fname)
        if src.exists():
            try:
                shutil.copy2(src, staging / src.name)
            except Exception:
                pass

    # Build DMG via hdiutil
    dmg_parent = target_dmg.parent
    dmg_parent.mkdir(parents=True, exist_ok=True)

    # If target exists, remove it
    if target_dmg.exists():
        target_dmg.unlink()

    volname = f"{APP_NAME}-{APP_VERSION}"
    cmd = [
        "hdiutil", "create",
        "-volname", volname,
        "-srcfolder", str(staging),
        "-ov",
        "-format", "UDZO",
        str(target_dmg)
    ]

    print("   Running:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
        print(f"DMG created at: {target_dmg}")
        return True
    except subprocess.CalledProcessError as e:
        print("hdiutil failed:", e)
        return False
    finally:
        # clean staging
        try:
            shutil.rmtree(staging)
        except Exception:
            pass


def create_archive():
    """
    Create platform-appropriate archive:
    - macOS: create .dmg containing the .app (uses create_dmg)
    - Windows: create .zip containing the built artifact (exe or folder)
    - Linux/other: create .tar.gz (gztar) containing the built artifact (folder or file)

    Relies on find_built_artifact() to locate the primary build output.
    """
    print("Creating distribution archive...")
    system = platform.system().lower()
    arch = platform.machine().lower()

    built = find_built_artifact()
    if not built:
        print("No built artifact found in dist/. Cannot create archive.")
        return False

    archive_basename = f"{APP_NAME}-v{APP_VERSION}-{system}-{arch}"
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # macOS: prefer creating a dmg from the .app bundle
    if system == "darwin":
        # If the found artifact isn't a .app, try to find one in dist/
        if not (built.exists() and built.is_dir() and built.suffix == ".app"):
            apps = list(DIST_DIR.glob("*.app"))
            if apps:
                built = apps[0]

        if not (built.exists() and built.is_dir() and built.suffix == ".app"):
            print("Built .app not found for DMG creation.")
            return False

        # Ensure permissions/xattrs are OK before creating dmg
        try:
            adjust_macos_app(built)
        except Exception:
            pass

        dmg_path = DIST_DIR / f"{archive_basename}.dmg"
        return create_dmg(built, dmg_path)

    # For Windows and Linux/other: create an archive (zip or tar.gz)
    staging = BUILD_DIR / "archive_temp"
    # ensure a clean staging area
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    try:
        # Copy the built artifact into staging by preserving its top-level name
        top_name = built.name
        dest = staging / top_name
        if built.is_dir():
            shutil.copytree(built, dest)
        else:
            shutil.copy2(built, dest)

        # Copy README/LICENSE if present
        for fname in ("README.md", "LICENSE"):
            src = Path(fname)
            if src.exists():
                shutil.copy2(src, staging / src.name)

        archive_path = DIST_DIR / archive_basename

        if system == "windows":
            # Create zip archive
            try:
                shutil.make_archive(str(archive_path), "zip", root_dir=str(staging), base_dir=top_name)
                final = f"{archive_path}.zip"
                print(f"Created archive: {final}")
                return True
            except Exception as e:
                print("Failed to create ZIP archive:", e)
                return False

        else:
            # Linux/other: create gzipped tarball
            try:
                shutil.make_archive(str(archive_path), "gztar", root_dir=str(staging), base_dir=top_name)
                final = f"{archive_path}.tar.gz"
                print(f"Created archive: {final}")
                return True
            except Exception as e:
                print("Failed to create tar.gz archive:", e)
                return False

    finally:
        # Cleanup staging directory
        try:
            if staging.exists():
                shutil.rmtree(staging)
        except Exception:
            pass


def print_build_info():
    """Print build information"""
    print(f"""
Build Information:
   Application: {APP_NAME} v{APP_VERSION}
   Platform: {platform.system()} {platform.release()}
   Architecture: {platform.machine()}
   Python: {sys.version.split()[0]}
   Build Directory: {BUILD_DIR.absolute()}
   Distribution Directory: {DIST_DIR.absolute()}
""")


def main():
    """Main build function"""
    print(f"Building {APP_NAME} v{APP_VERSION}")
    print("=" * 50)

    print_build_info()

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    ensure_paths()

    # Clean previous builds
    clean_build()

    # Create directories
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # Run PyInstaller build
    if not build_with_pyinstaller():
        sys.exit(1)

    # Create archive (dmg/zip/tar.gz)
    if not create_archive():
        sys.exit(1)

    print("\nBuild completed successfully!")
    print(f"Check the '{DIST_DIR}' directory for output files")


if __name__ == "__main__":
    main()
