import py_compile
import os

CLI_DIR = os.path.join(os.path.dirname(__file__), "../../../tools/cli")


def test_all_cli_files_compile():
    for f in sorted(os.listdir(CLI_DIR)):
        if f.endswith(".py"):
            path = os.path.join(CLI_DIR, f)
            py_compile.compile(path, doraise=True)
