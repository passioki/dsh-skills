# -*- coding: utf-8 -*-
"""dsh-skills 自检 —— 技能必须既"通用"又"真能跑"。

用法:
    python verify.py          # 打印每条结果，失败则 exit 1
    python verify.py -v       # 额外打印每个被检查的文件

四道检查（**每条都能真的变红**，不是恒真）：

| # | 检查 | 为什么 |
|---|---|---|
| ① | `skills/` 下**不许出现盘符绝对路径**（`X:\\` / `X:/`） | 通用性：换机器/换盘必须能用 |
| ② | 每个 `*.ps1` 必须是**纯 ASCII** | Windows PowerShell 5.1 读**无 BOM 的 UTF-8** `.ps1` 会按 GBK 解码 -> 中文字面量**破坏解析**（实测踩过）。不靠"BOM 能活下来" |
| ③ | 每个 `*.ps1` 能被 PowerShell **解析** | 语法门禁；非 Windows 自动跳过 |
| ④ | **端到端**：在**临时目录**里造最小 `session.v4.jsonl` -> `extract.py` -> `index_gen.py` -> `prog_gen.py`，断言产物正确 | 全程**不碰本项目任何文件** -> 这就是"在别的项目里也能跑"的证据 |
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# 通用工具在 GBK 控制台上 print 非 GBK 字符会【崩】（实测：'->' U+21D2）
#   -> ① 强制 stdout 用 UTF-8 且 errors='replace'（永不抛）
#      ② 本文件自己的提示语**只用 ASCII**（在 GBK 终端里也能读）
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

REPO = Path(__file__).resolve().parent
SKILLS = REPO / 'skills'
VERBOSE = '-v' in sys.argv

DRIVE = re.compile(r'[A-Za-z]:[\\/]')
fails = []


def ok(msg):
    print('  OK   %s' % msg)


def bad(check, msg):
    print('  FAIL %s' % msg)
    fails.append('%s: %s' % (check, msg))


def text_files():
    for p in sorted(SKILLS.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            yield p


# ---------------------------------------------------------------- ① 通用性
def check_no_drive_paths():
    print('[1] 通用性：skills/ 下不得出现盘符绝对路径')
    hits = []
    for p in text_files():
        try:
            txt = p.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        for i, line in enumerate(txt.split('\n'), 1):
            if DRIVE.search(line):
                hits.append('%s:%d: %s' % (p.relative_to(REPO).as_posix(), i,
                                           line.strip()[:80]))
        if VERBOSE:
            print('       checked %s' % p.relative_to(REPO).as_posix())
    if hits:
        bad('通用性', '发现 %d 处盘符绝对路径：\n       %s'
            % (len(hits), '\n       '.join(hits[:10])))
    else:
        ok('没有盘符绝对路径')


# ------------------------------------------------------- ② PS 必须纯 ASCII
def check_ps_ascii():
    print('[2] PS 可移植性：*.ps1 必须纯 ASCII')
    ps = [p for p in text_files() if p.suffix.lower() == '.ps1']
    if not ps:
        bad('PS', '没找到任何 .ps1 —— 检查范围是不是错了？')
        return
    for p in ps:
        raw = p.read_bytes()
        hi = sum(1 for b in raw if b > 127)
        if hi:
            bad('PS', '%s 有 %d 个非 ASCII 字节（PS 5.1 会按 GBK 解码 -> 可能解析失败）'
                % (p.relative_to(REPO).as_posix(), hi))
        else:
            ok('%s 纯 ASCII' % p.relative_to(REPO).as_posix())


# ------------------------------------------------------------ ③ PS 语法
def check_ps_parses():
    print('[3] PS 语法：每个 *.ps1 都要能解析')
    if not shutil.which('powershell') and not shutil.which('pwsh'):
        print('  SKIP 本机没有 PowerShell（非 Windows）')
        return
    exe = shutil.which('powershell') or shutil.which('pwsh')
    for p in text_files():
        if p.suffix.lower() != '.ps1':
            continue
        cmd = ("$e=$null; [void][System.Management.Automation.Language.Parser]"
               "::ParseFile('%s',[ref]$null,[ref]$e); if($e){$e|%%{$_.Message}; exit 1}"
               % str(p))
        r = subprocess.run([exe, '-NoProfile', '-ExecutionPolicy', 'Bypass',
                            '-Command', cmd], capture_output=True, text=True)
        if r.returncode != 0:
            bad('PS 语法', '%s 解析失败: %s'
                % (p.relative_to(REPO).as_posix(), (r.stdout or r.stderr).strip()[:200]))
        else:
            ok('%s 解析通过' % p.relative_to(REPO).as_posix())


# ------------------------------------------------------------ ④ 端到端
MIN_JSONL = [
    {'type': 'user/message', 'time': 1760000000000,
     'data': {'source': {'kind': 'user'},
              'content': [{'type': 'text', 'text': '第一条用户发言：谈调度与队列。'}]}},
    {'type': 'assistant/message', 'time': 1760000060000,
     'data': {'message': {'content': [{'type': 'text', 'text': '助手回复：谈 next_run。'}]}}},
    {'type': 'user/message', 'time': 1760007200000,
     'data': {'source': {'kind': 'user'},
              'content': [{'type': 'text', 'text': '第二条用户发言：谈测试与守卫。'}]}},
]


def run(script, *args, cwd):
    py = sys.executable
    r = subprocess.run([py, str(script)] + [str(a) for a in args],
                       capture_output=True, text=True, cwd=str(cwd))
    return r


def check_end_to_end():
    print('[4] 端到端：在临时目录里跑完整流程（不碰本项目）')
    tmp = Path(tempfile.mkdtemp(prefix='dshskills-verify-'))
    try:
        scripts = SKILLS / 'session-memory' / 'scripts'
        (tmp / 'session.v4.jsonl').write_text(
            '\n'.join(json.dumps(x, ensure_ascii=False) for x in MIN_JSONL),
            encoding='utf-8')

        r = run(scripts / 'extract.py', 'session.v4.jsonl', '_both.txt', cwd=tmp)
        if r.returncode != 0 or not (tmp / '_both.txt').is_file():
            bad('端到端', 'extract.py 失败: %s' % (r.stdout + r.stderr).strip()[:200])
            return
        both = (tmp / '_both.txt').read_text(encoding='utf-8')
        if 'USER' not in both or 'ASST' not in both:
            bad('端到端', '_both.txt 里没有 USER/ASST 标题')
            return
        ok('extract.py -> _both.txt（%d 字节）' % len(both.encode('utf-8')))

        r = run(scripts / 'index_gen.py', '_both.txt', 'SESSION-INDEX.md', cwd=tmp)
        idx = tmp / 'SESSION-INDEX.md'
        if r.returncode != 0 or not idx.is_file():
            bad('端到端', 'index_gen.py 失败: %s' % (r.stdout + r.stderr).strip()[:200])
            return
        itxt = idx.read_text(encoding='utf-8')
        if '| 用户发言 | 2 |' not in itxt:
            bad('端到端', 'SESSION-INDEX.md 的用户发言计数不对（期望 2）')
            return
        ok('index_gen.py -> SESSION-INDEX.md（用户发言 2 条 ok）')

        r = run(scripts / 'prog_gen.py', '_both.txt', 'DESIGN-SPEC-PROGRESS.md', cwd=tmp)
        ptxt = (tmp / 'DESIGN-SPEC-PROGRESS.md')
        if r.returncode != 0 or not ptxt.is_file():
            bad('端到端', 'prog_gen.py 失败: %s' % (r.stdout + r.stderr).strip()[:200])
            return
        p = ptxt.read_text(encoding='utf-8')
        if '## 分段覆盖' not in p:
            bad('端到端', 'PROGRESS 里没有"分段覆盖"表')
            return
        # 默认名必须仍是历史默认（老项目零配置行为不变）
        if '`DESIGN-SPEC.md`' not in p:
            bad('端到端', '默认文档名不再是 DESIGN-SPEC.md（老项目向后兼容被破坏）')
            return
        ok('prog_gen.py -> DESIGN-SPEC-PROGRESS.md（默认名向后兼容 ok）')

        # 再验一次"可覆盖"：写配置文件，改用别的名字
        (tmp / 'session-memory.config.json').write_text(
            json.dumps({'spec': 'MY-SPEC.md', 'index': 'IDX.md'}), encoding='utf-8')
        r = run(scripts / 'prog_gen.py', '_both.txt', 'P2.md', cwd=tmp)
        p2 = (tmp / 'P2.md').read_text(encoding='utf-8') if (tmp / 'P2.md').is_file() else ''
        if 'MY-SPEC.md' not in p2 or 'IDX.md' not in p2:
            bad('端到端', '配置文件没有生效（期望正文里出现 MY-SPEC.md / IDX.md）')
            return
        ok('配置文件生效（spec/index 被覆盖 ok）')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    print('dsh-skills self-check  (repo: %s)' % REPO)
    print('')
    check_no_drive_paths()
    print('')
    check_ps_ascii()
    print('')
    check_ps_parses()
    print('')
    check_end_to_end()
    print('')
    if fails:
        print('FAILED (%d):' % len(fails))
        for f in fails:
            print('   - %s' % f)
        return 1
    print('ALL CHECKS PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
