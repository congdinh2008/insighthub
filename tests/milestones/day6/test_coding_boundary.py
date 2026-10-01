"""Untrusted diffs cannot replace the fixed verifier or create executable paths."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "coding_client", ROOT / "tools/coding/day6/client.py"
)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
PATCH = "--- a/task.py\n+++ b/task.py\n@@ -1 +1 @@\n-old\n+new\n"


@pytest.mark.parametrize(
    "path",
    [
        "../task.py",
        "/tmp/task.py",
        "check.py",
        ".env",
        "scripts/verify.py",
        "a/../../task.py",
    ],
)
def test_patch_path_escape_and_verifier_rejected(path):
    with pytest.raises(ValueError):
        client.validate_patch(PATCH.replace("task.py", path))


@pytest.mark.parametrize(
    "metadata",
    [
        "new file mode 120000",
        "new mode 100755",
        "rename to task.py",
        "GIT binary patch",
        "copy from .env",
    ],
)
def test_symlink_executable_rename_and_binary_patch_rejected(metadata):
    with pytest.raises(ValueError):
        client.validate_patch(metadata + "\n" + PATCH)


def test_second_file_cannot_be_smuggled():
    with pytest.raises(ValueError):
        client.validate_patch(PATCH + PATCH.replace("task.py", "check.py"))


def test_bounded_task_patch_accepted():
    assert client.validate_patch(PATCH) == PATCH
