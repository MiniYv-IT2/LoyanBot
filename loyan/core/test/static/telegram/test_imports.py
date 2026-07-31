import py_compile
import os

TELEGRAM_DIR = os.path.join(
    os.path.dirname(__file__),
    "../../../loyan_adapter/platform/telegram",
)


def test_all_files_compile():
    for f in sorted(os.listdir(TELEGRAM_DIR)):
        if f.endswith(".py"):
            path = os.path.join(TELEGRAM_DIR, f)
            py_compile.compile(path, doraise=True)
