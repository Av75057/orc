import subprocess, sys, os

src_main = os.path.join(os.path.dirname(__file__), "..", "src", "grace", "__main__.py")
result = subprocess.run(
    [sys.executable, src_main] + sys.argv[1:],
    cwd=os.path.dirname(os.path.dirname(__file__)),
)
sys.exit(result.returncode)
