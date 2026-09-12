import sys
import os

# Ensure both code directory and repository root are on Python path
code_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(code_dir, '..'))

if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

if __name__ == '__main__':
    from src.main import main
    main()
