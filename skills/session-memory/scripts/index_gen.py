# -*- coding: utf-8 -*-
"""生成 SESSION-INDEX.md（每条对话的【分类标签】+ 处置状态）。

用法:
    python index_gen.py <_both.txt> <输出 SESSION-INDEX.md>

★ 分类 = 标签，**可有交集**（一条可同时属于 调度/记录/前端…），不写死。
"""
import io
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

RULES = OrderedDict([
    ('调度', ('调度', '排期', 'next_run', '播放头', '队列', '顺序', '循环',
              '乱序', '插队', '优先级', 'pending', 'waiting', '门',
              'target', 'loop', '轮', 'window', '窗口', 'period', '周期')),
    ('记录', ('entry_id', '临时记录', '总记录', 'runs', 'total_runs',
              '计数', 'count', 'task_state', '记录', '颗粒度',
              '启动时间', '比对', '完成', '门票', '券', '归档')),
    ('前端', ('前端', '界面', 'UI', '按钮', 'tooltip', '悬停', '白屏',
              '溢出', 'overflow', '布局', '颜色', '标签', '拖', '抽屉',
              '简报', '导航', '顶栏', '下拉', 'OASX', 'oasx', '吸顶',
              '滚动', '弹窗', '图标')),
    ('环境', ('flutter', 'Flutter', '编译', '构建', 'build', 'OASX-src',
              'OASX-clean', 'OASX-app', '仓库', 'git', '推送', 'push',
              'exe', '双击', '管理员', '权限', 'sdk', 'SDK', '版本',
              '环境', '安装', '下载', '解压', '子代理', '卡住')),
    ('bug', ('bug', 'BUG', '报错', '异常', '崩溃', '卡死', '挂了',
             '不生效', '没反应', '不工作', '失败', '错误', '没变',
             '没通过', '依然', '还是不对', '问题', '不对', '重复',
             '冗余', '遗漏')),
    ('测试', ('测试', 'test', 'pytest', '守卫', '断言', 'passed',
              'failed', '验证', '复现', '污染')),
    ('文档', ('文档', 'memory', 'Memory', '台账', 'ledger', '设计规格',
              '纪要', '写进文档', '更新文档', '记录文档')),
])
OTHER = '其他'


def classify(text):
    low = text.lower()
    tags = [t for t, kws in RULES.items() if any(k.lower() in low for k in kws)]
    return tags or [OTHER]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
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

    cu = sum(1 for e in ent if e[0] == 'USER')
    tc = Counter()
    for _, _, txt in ent:
        for tg in classify(txt):
            tc[tg] += 1

    out = ['# 会话索引（分类标签 + 处置状态）', '',
           '> ★ 用途：**按主题查找**「哪次对话谈过什么」+ **核查覆盖率**。',
           '> ★ 分类是**标签**，★ **可有交集**（一条可属多个）。', '',
           '## 统计', '', '| 项 | 数 |', '|---|---|',
           '| 用户发言 | %d |' % cu,
           '| 助手回复 | %d |' % (len(ent) - cu),
           '| 合计 | %d |' % len(ent), '',
           '| 分类 | 条数 |', '|---|---|']
    for tg, n in tc.most_common():
        out.append('| %s | %d |' % (tg, n))
    out += ['', '## 明细', '',
            '| # | 时间 | 谁 | 分类 | 处置 | 首行 |', '|---|---|---|---|---|---|']
    for i, (w_, t_, txt) in enumerate(ent, 1):
        first = txt.split('\n')[0].strip()[:60].replace('|', '\\|')
        out.append('| %d | %s | %s | %s | ⬜待处理 | %s |'
                   % (i, t_, 'U' if w_ == 'USER' else 'A',
                      '/'.join(classify(txt)), first))

    dst.write_text('\n'.join(out), encoding='utf-8')
    print('OK -> %s' % dst)
    print('   entries=%d (U=%d A=%d)' % (len(ent), cu, len(ent) - cu))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
