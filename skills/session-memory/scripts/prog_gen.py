# -*- coding: utf-8 -*-
"""生成「覆盖台账」文档（按时间分段，逐段标状态）。

用法:
    python prog_gen.py <_both.txt> <输出文件> [--config <cfg.json>]

★ 通用化：输出文件名**由你给**（第 2 个参数）；正文里引用的文档名走 `_conf.py`
  （默认 `DESIGN-SPEC.md` / `SESSION-INDEX.md`，★ 可用 `session-memory.config.json` 覆盖）。

★ 按【每 2 小时】切成段，逐段标状态（⬜未读 / 🔄进行中 / ✅已读）。
★ 每轮读完一段，把该段的 `⬜ 未读 | —` 改成 `✅ 已读 | 进文档 §x`。
"""
import re
import sys
from collections import OrderedDict
from pathlib import Path

import _conf

HEAD = """# 设计规格书 · **覆盖台账**（可核查）

> ★ 用途：★ **证明"读到哪里了"**，防止漏读。
>
> ★ 铁律（违反即返工）：
>
> | # | 规则 |
> |---|---|
> | R1 | ★ **全覆盖遍历**：按时间顺序读**全部**发言与回复，不用关键词当范围 |
> | R2 | ★ **每轮报覆盖率**：没有覆盖率报告 = 本轮不算完成 |
> | R3 | ★ **禁止"首行预览"当读过**：截断输出不计入已读 |
> | R4 | ★ **每条必标处置**：`进文档 §x` / `无设计信息` / `待处理` |
> | R5 | ★ **回读校验**：每段抽 3~5 条回原文核对 |
> | R6 | ★ **分歧块进 §5 台账** |
"""


def main():
    conf, argv = _conf.load()
    if len(argv) < 2:
        print(__doc__)
        return 1
    src, dst = Path(argv[0]), Path(argv[1])
    index_name = conf['index']
    spec_name = conf['spec']
    lines = src.read_text(encoding='utf-8', errors='replace').split('\n')

    ent, who, t, buf = [], None, None, []

    def flush():
        if who is not None:
            txt = '\n'.join(buf).strip()
            if txt:
                ent.append((who, t, txt))

    for l in lines:
        m = re.match(r'^======== (USER|ASST) \[([\d\-]+ [\d:]+)\] ========$', l)
        if m:
            flush()
            who, t, buf = m.group(1), m.group(2), []
            continue
        if who is not None:
            buf.append(l)
    flush()

    byday = OrderedDict()
    for w_, t_, txt in ent:
        byday.setdefault(t_.split(' ')[0], []).append((w_, t_))

    out = [HEAD, '', '## 总量', '',
           '| 项 | 数 |', '|---|---|',
           '| 用户发言 | %d |' % sum(1 for e in ent if e[0] == 'USER'),
           '| 助手回复 | %d |' % sum(1 for e in ent if e[0] == 'ASST'),
           '| **合计** | **%d** |' % len(ent), '',
           '## 分段覆盖（★ 每轮更新这里）', '',
           '| # | 日期 | 时段 | 条数(U/A) | 状态 | 进文档章节 |',
           '|---|---|---|---|---|---|']

    idx = 0
    for day, items in byday.items():
        blocks = OrderedDict()
        for w_, t_ in items:
            hh = int(t_.split(' ')[1].split(':')[0])
            key = '%s %02d:00-%02d:59' % (day, hh - hh % 2, hh - hh % 2 + 1)
            blocks.setdefault(key, []).append(w_)
        for key, ws in blocks.items():
            idx += 1
            u = sum(1 for x in ws if x == 'USER')
            out.append('| %d | %s | %s | %d/%d | ⬜ 未读 | — |'
                       % (idx, day, key.split(' ')[1], u, len(ws) - u))

    out += ['', '## 主题索引（按分类查）', '',
            '★ 每条对话的分类标签见：★ [`%s`](%s)' % (index_name, index_name),
            '',
            '| 主题 | 筛什么标签 |', '|---|---|',
            '| 调度（执行顺序/播放头/队列/暂停）| `调度` |',
            '| 记录（entry_id/runs/计数/完成）| `记录` |',
            '| 前端（界面/白屏/按钮/布局）| `前端` |',
            '| 环境（flutter/构建/仓库/exe）| `环境` |',
            '| bug 报告 | `bug` |',
            '| 测试与验证 | `测试` |',
            '| 文档与台账 | `文档` |', '',
            '## 已读发现', '',
            '★ 每读完一段，在这里追加"设计点"，★ 并按主题分组。',
            '★ 同时把要点**写进 `%s`**（边读边写）。' % spec_name, '']

    dst.write_text('\n'.join(out), encoding='utf-8')
    print('OK -> %s (%d 段)' % (dst, idx))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
