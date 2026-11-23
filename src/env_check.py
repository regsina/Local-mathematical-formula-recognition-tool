import platform
import shutil
import subprocess
from dataclasses import dataclass

from . import config


@dataclass
class CheckItem:
    name: str
    ok: bool
    detail: str


def check_windows() -> CheckItem:
    version = platform.version()
    release = platform.release()
    ok = platform.system() == "Windows"
    return CheckItem("操作系统", ok, f"{platform.system()} {release}（{version}）")


def check_gpu() -> CheckItem:
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return CheckItem("显卡与驱动", True, out.stdout.strip().splitlines()[0])
        return CheckItem("显卡与驱动", False, "nvidia-smi 未返回显卡信息")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckItem("显卡与驱动", False, f"无法检测（{exc}）")


def check_disk_space(required_gb: float = 8.0) -> CheckItem:
    try:
        free = shutil.disk_usage(config.data_dir()).free
        free_gb = free / 1024 / 1024 / 1024
        ok = free_gb >= required_gb
        return CheckItem(
            "磁盘空间",
            ok,
            f"剩余 {free_gb:.1f} GB（模型与历史预计需要 {required_gb:.0f} GB，拟定值）",
        )
    except OSError as exc:
        return CheckItem("磁盘空间", False, str(exc))


def check_python() -> CheckItem:
    v = platform.python_version()
    major, minor, _ = (int(x) for x in v.split("."))
    ok = (major, minor) >= (3, 10)
    return CheckItem("Python 运行环境", ok, f"Python {v}")


def run_all_checks() -> list[CheckItem]:
    return [check_windows(), check_python(), check_gpu(), check_disk_space()]


def blocking_failures(items: list[CheckItem]) -> list[CheckItem]:
    return [
        item
        for item in items
        if not item.ok and item.name in ("操作系统", "Python 运行环境")
    ]
