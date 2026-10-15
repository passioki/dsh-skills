# -*- coding: utf-8 -*-
"""从 DSH 会话 jsonl 导出【双向】纯文本（USER/ASST + 真实时间戳）。

用法:
    python extract.py <session.v4.jsonl> [输出路径]

★ 时区: jsonl 里 time 是 UTC 毫秒; 本机 UTC+8 => 换算后才是真实时间。
输出格式（供 seg.ps1 切段）:
    ======== USER [MM-DD HH:MM:SS] ========
    <正文>
"""
import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ = timezone(timedelta(hours=8))
SKIP_USER = (
    'Current runtime context.', '<system-reminder>',
    'Background subagent', '[Request interrupted',
    'This is an automatically generated checkpoint',
)


def fmt(ms):
    if not isinstance(ms, (int, float)):
        return '?'
    return datetime.fromtimestamp(ms / 1000.0, TZ).strftime('%m-%d %H:%M:%S')


def texts(content):
    parts = []
    if isinstance(content, list):
        for it in content:
            if isinstance(it, dict):
                if it.get('type') == 'text':
                    parts.append(str(it.get('text') or ''))
                elif it.get('type') == 'tool_use':
                    parts.append('[调用工具 %s]' % it.get('name'))
            elif isinstance(it, str):
                parts.append(it)
    elif isinstance(content, str):
        parts.append(content)
    return '\n'.join(parts)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent / '_both.txt'

    rows = []
    with src.open('r', encoding='utf-8', errors='replace') as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            ty = d.get('type')
            if ty == 'user/message':
                dd = d.get('data') or {}
                if str((dd.get('source') or {}).get('kind')) != 'user':
                    continue
                t = texts(dd.get('content'))
                if not t.strip():
                    continue
                if any(t.lstrip().startswith(s) for s in SKIP_USER):
                    continue
                rows.append(('USER', d.get('time'), t))
            elif ty == 'assistant/message':
                dd = d.get('data') or {}
                msg = dd.get('message') if isinstance(dd.get('message'),
                                                      dict) else dd
                t = texts((msg or {}).get('content'))
                if t.strip():
                    rows.append(('ASST', d.get('time'), t))

    rows.sort(key=lambda r: r[1] or 0)
    out = []
    for who, ms, txt in rows:
        out.append('')
        out.append('======== %s [%s] ========' % (who, fmt(ms)))
        out.append(txt.rstrip())

    dst.write_text('\n'.join(out), encoding='utf-8')
    nu = sum(1 for r in rows if r[0] == 'USER')
    print('OK -> %s' % dst)
    print('   USER=%d ASST=%d 合计=%d' % (nu, len(rows) - nu, len(rows)))
    if rows:
        print('   时间范围: %s -> %s' % (fmt(rows[0][1]), fmt(rows[-1][1])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
