#!/usr/bin/env python3
"""官方工程导入、框架字节校验和联合自测；仅依赖 Python 标准库。"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TASKS = ("pingpang", "basketball")
BASELINE = ROOT / "docs" / "framework-sha256.json"


def excluded(path):
    parts = path.parts
    if "__pycache__" in parts or path.suffix == ".pyc":
        return True
    if parts[0] in ("input", "output"):
        return True
    if len(parts) > 1 and parts[0] in TASKS:
        if parts[1] == "public_data":
            return True
        if parts[1] == "participant":
            return True
    return False


def hashes(root):
    result = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if excluded(rel):
            continue
        if path.is_symlink():
            raise ValueError(f"框架中不允许符号链接：{rel}")
        if path.is_file():
            result[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def require_structure(root):
    required = [root / "run_all.sh"]
    for task in TASKS:
        required += [root / task / "run.py", root / task / "participant" / "solution.py"]
        if not (root / task / "core").is_dir():
            raise ValueError(f"缺少官方目录：{task}/core")
    for path in required:
        if not path.is_file():
            raise ValueError(f"缺少官方文件：{path.relative_to(root)}")


def import_official(archive):
    target = ROOT / "participant"
    if target.exists() or BASELINE.exists():
        raise ValueError("已存在 participant/ 或校验记录；为保护已有代码，拒绝覆盖。")
    with tempfile.TemporaryDirectory(prefix="official-", dir=ROOT) as tmp:
        stage = Path(tmp)
        with zipfile.ZipFile(archive) as package:
            names = {item.filename for item in package.infolist()}
            prefix = (
                ("participant", "participant")
                if "participant/participant/run_all.sh" in names
                else ("participant",)
            )
            seen = set()
            for item in package.infolist():
                rel = PurePosixPath(item.filename)
                if not rel.parts or rel.parts[0] == "__MACOSX":
                    continue
                if (rel.is_absolute() or ".." in rel.parts or "\\" in item.filename
                        or any(":" in p for p in rel.parts) or rel.parts[:len(prefix)] != prefix):
                    if item.is_dir() and rel.parts == ("participant",) and len(prefix) == 2:
                        continue
                    raise ValueError(f"不符合 participant/ 根目录约定的路径：{item.filename}")
                rel = PurePosixPath("participant", *rel.parts[len(prefix):])
                kind = stat.S_IFMT(item.external_attr >> 16)
                if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise ValueError(f"压缩包包含非普通文件：{item.filename}")
                if rel in seen:
                    raise ValueError(f"压缩包包含重复路径：{item.filename}")
                seen.add(rel)
                dest = stage.joinpath(*rel.parts)
                if item.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with package.open(item) as source, dest.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    # ZIP 在 Windows 下可能丢失执行位；仅补 shell 执行权限，不改文件内容。
                    dest.chmod(0o755 if dest.suffix == ".sh" or item.external_attr >> 16 & 0o111 else 0o644)
        official = stage / "participant"
        require_structure(official)
        baseline = hashes(official)
        official.rename(target)
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("已导入官方工程；两个任务的参考实现均原样保留。")


def check():
    root = ROOT / "participant"
    require_structure(root)
    if not BASELINE.is_file():
        raise ValueError("缺少首次导入的框架校验记录。请使用 import 命令导入原始官方工程。")
    expected = json.loads(BASELINE.read_text(encoding="utf-8"))
    actual = hashes(root)
    changed = sorted(key for key in expected.keys() | actual.keys() if expected.get(key) != actual.get(key))
    if changed:
        raise ValueError("检测到参赛代码区以外的变动：\n" + "\n".join(changed))
    print("框架文件与首次导入版本一致（本地辅助校验，不替代官方自检）。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("import", help="原样导入官方 participant.zip，拒绝覆盖")
    command.add_argument("archive", type=Path)
    commands.add_parser("check", help="校验官方框架是否被改动")
    args = parser.parse_args()
    try:
        if args.command == "import":
            import_official(args.archive)
        elif args.command == "check":
            check()
        else:
            check()
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"错误：{exc}\n")


if __name__ == "__main__":
    main()
