import subprocess
import sys

NAV_INPUT = """
9
0

2
0
2
1
0
2
2
0
2
3
0
3



1
1




0
0
"""


SEARCH_INPUT = """
1
1
kljwwdlkjadkljakdl


q
0
0
"""


def test_navigation_all_menus():
    """Invalid option, settings (all langs), FAQ, empty username input, back/exit."""
    _run("test_navigation", NAV_INPUT.lstrip(), timeout=10, check_goodbye=True)


def test_search_random_username():
    """Search with random string — should complete without crash."""
    _run("test_search", SEARCH_INPUT.lstrip(), timeout=90, check_goodbye=False)


def _run(name: str, input_data: str, timeout: int, check_goodbye: bool = True):
    proc = subprocess.Popen(
        ["pyscratrace"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(input=input_data, timeout=timeout)
        assert proc.returncode == 0, f"{name}: exit {proc.returncode}\nstderr({len(stderr)}):\n{stderr}"
        if check_goodbye:
            assert "Goodbye" in stdout, f"{name}: missing Goodbye in output"
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        assert False, f"{name}: Timed out ({timeout}s) — stdout: {stdout[-500:]}\nstderr: {stderr[-500:]}"
