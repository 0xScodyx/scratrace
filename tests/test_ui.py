import subprocess
def test_pyscratrace_starts():
    proc = subprocess.Popen(
        ["pyscratrace"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    try:
        stdout, stderr = proc.communicate(input="0\n", timeout=3)
        assert proc.returncode == 0
        assert "Goodbye!" in stdout
    except subprocess.TimeoutExpired:
        proc.kill()
        assert False
