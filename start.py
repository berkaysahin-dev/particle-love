import importlib.util
import shutil
import subprocess
import sys

SCRIPT = "love.py"


def ensure_deps():
    need = ("numpy", "cv2", "PIL", "pygments")
    if all(importlib.util.find_spec(m) for m in need):
        return
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])


def main():
    ensure_deps()
    print(f"\n  1) Run live animation ({SCRIPT})")
    print(f"  2) Save MP4 animation (out/love.mp4)")
    print(f"  3) Render vertical reel (out/love_reel.mp4)\n")
    choice = input("Select [1/2/3] (default 1): ").strip() or "1"

    if choice in ("2", "3") and not shutil.which("ffmpeg"):
        print("ffmpeg was not found on PATH. Install it first to export MP4.")
        return 1

    if choice == "1":
        return subprocess.call([sys.executable, SCRIPT])
    if choice == "2":
        return subprocess.call([sys.executable, SCRIPT, "--save"])
    if choice == "3":
        return subprocess.call([sys.executable, "make_reel.py"])
    print("Invalid option.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())