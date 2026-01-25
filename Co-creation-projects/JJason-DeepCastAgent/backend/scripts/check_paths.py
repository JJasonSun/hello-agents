import sys
import os
from pathlib import Path

# 添加 src 到 sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config import Configuration, BACKEND_ROOT

def main():
    print(f"BACKEND_ROOT: {BACKEND_ROOT}")
    
    config = Configuration.from_env()
    
    print(f"Audio Output Dir: {config.audio_output_dir}")
    print(f"Notes Workspace: {config.notes_workspace}")

if __name__ == "__main__":
    main()
