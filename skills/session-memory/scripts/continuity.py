# -*- coding: utf-8 -*-
"""session-memory 连续运行辅助：初始化/查看断点续接卡（RESUME + RESUME-INDEX）。

用法（在项目根目录跑；配置走 session-memory.config.json / --config / 环境变量）：

  python continuity.py init [--root <项目根>] [--task-id <ID>] [--objective "<一句话目标>"] [--force]
  python continuity.py status [--root <项目根>]

设计原则：
  * 只创建缺失文件；已有文件默认**不覆盖**（--force 才覆盖，危险操作前先备份）；
  * 路径完全由 `_conf` 决定（docs_dir / resume / resume_index 可配）；
  * 模板来自技能目录 `templates/`，不改脚本即可换项目；
  * 本脚本只负责"起卡片"，真正的断点内容由模型在每轮按 SKILL.md 强制 6 填写。
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _conf  # noqa: E402


def _utf8_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _skill_templates() -> Path:
    return Path(__file__).resolve().parent.parent / "templates"


def _read_template(name: str) -> str:
    p = _skill_templates() / name
    if not p.is_file():
        raise SystemExit(f"continuity: template not found: {p}")
    return p.read_text(encoding="utf-8")


def _now() -> str:
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def cmd_init(root: Path, task_id: str, objective: str, force: bool) -> int:
    conf, _ = _conf.load([])
    resume = root / _conf.doc_path(conf, "resume")
    index = root / _conf.doc_path(conf, "resume_index")
    docs = resume.parent
    docs.mkdir(parents=True, exist_ok=True)

    task_id = task_id.strip() or "TASK-ID"
    objective = objective.strip() or "<一句话目标：可判定，不要写'优化一下'>"

    if resume.exists() and not force:
        print(f"skip (exists): {resume}")
    else:
        text = _read_template("RESUME.template.md")
        text = text.replace("<TASK-ID>", task_id)
        text = text.replace("<用户要什么，验收即什么；不要写成\"优化一下\"这种不可判定目标>", objective)
        text = text.replace("<N>", "1")
        text = text.replace("<YYYY-MM-DDTHH:MM:SS+08:00>", _now())
        text = text.replace("<phase-gate | tool-ops | chars | compaction | turn-end | manual>", "manual")
        _write(resume, text)
        print(f"created: {resume}")

    if index.exists() and not force:
        print(f"skip (exists): {index}")
    else:
        text = _read_template("RESUME-INDEX.template.md")
        text = text.replace("TASK-ID", task_id)
        _write(index, text)
        print(f"created: {index}")

    print("下一步：按 SKILL.md 强制 6 填写验收清单/下一步命令；每轮结束前更新两张卡。")
    return 0


def _grab(text: str, key: str) -> str:
    m = re.search(rf"^\s*{re.escape(key)}:\s*(.*)$", text, re.MULTILINE)
    if not m:
        return ""
    return m.group(1).split("#", 1)[0].strip()


def cmd_status(root: Path) -> int:
    conf, _ = _conf.load([])
    resume = root / _conf.doc_path(conf, "resume")
    index = root / _conf.doc_path(conf, "resume_index")
    print(f"docs_dir   = {conf.get('docs_dir')}")
    print(f"resume     = {resume}")
    print(f"resume_idx = {index}")
    print(f"checkpoint_ops   = {conf.get('checkpoint_ops')}")
    print(f"checkpoint_chars = {conf.get('checkpoint_chars')}")

    if not resume.is_file():
        print("WARN: RESUME.md missing -> run `continuity.py init`")
    else:
        text = resume.read_text(encoding="utf-8", errors="replace")
        print(
            "RESUME: seq={} status={} updated_at={} trigger={}".format(
                _grab(text, "checkpoint_seq") or "?",
                _grab(text, "status") or "?",
                _grab(text, "updated_at") or "?",
                _grab(text, "trigger") or "?",
            )
        )
        todo = len(re.findall(r"^- \[ \]", text, re.MULTILINE))
        done = len(re.findall(r"^- \[[xX]\]", text, re.MULTILINE))
        print(f"acceptance: {done} done / {done + todo} total")

    if not index.is_file():
        print("WARN: RESUME-INDEX.md missing -> run `continuity.py init`")
    else:
        rows = [
            ln
            for ln in index.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.strip().startswith("|") and not re.match(r"^\|\s*-+", ln.strip())
        ]
        # drop header row(s): only rows whose first cell is an integer seq
        data = [r for r in rows if re.match(r"^\|\s*\d+\s*\|", r)]
        print(f"RESUME-INDEX: {len(data)} checkpoint row(s)")
        if data:
            print("latest:", data[-1])
    return 0


def main(argv=None) -> int:
    _utf8_stdout()
    ap = argparse.ArgumentParser(description="session-memory continuity helper")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="create RESUME.md + RESUME-INDEX.md from templates")
    p_init.add_argument("--root", default=".", help="project root (default: cwd)")
    p_init.add_argument("--task-id", default="TASK-ID")
    p_init.add_argument("--objective", default="")
    p_init.add_argument("--force", action="store_true", help="overwrite existing files")

    p_status = sub.add_parser("status", help="print continuity paths/seq/acceptance counts")
    p_status.add_argument("--root", default=".", help="project root (default: cwd)")

    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    if args.cmd == "init":
        return cmd_init(root, args.task_id, args.objective, args.force)
    return cmd_status(root)


if __name__ == "__main__":
    raise SystemExit(main())
