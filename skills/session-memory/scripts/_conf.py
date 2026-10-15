# -*- coding: utf-8 -*-
"""session-memory 的【项目配置】解析 —— ★ 通用化的核心。

★ 设计原则：**默认值 = 本技能的历史默认** ⇒ ★ 老项目**零配置**、行为不变；
  ★ 换到别的项目时**只覆盖要改的键**，★ 不用改任何脚本。

解析顺序（后面覆盖前面）：
  ① 内置 `DEFAULT`
  ② 配置文件：`--config <path>`  >  `./session-memory.config.json`  >  `$SESSION_MEMORY_CONFIG`
  ③ 环境变量：`SESSION_MEMORY_<KEY>`（例如 `SESSION_MEMORY_SPEC`）

键（全部可选）：
  docs_dir  文档目录            默认 `docs`
  spec      主体规格书名        默认 `DESIGN-SPEC.md`
  progress  覆盖台账名          默认 `DESIGN-SPEC-PROGRESS.md`
  index     分类索引名          默认 `SESSION-INDEX.md`
  ledger    未完成台账名        默认 `PENDING-LEDGER.md`
  input     extract.py 导出的对话文本   默认 `_both.txt`
  tags      分类关键词表 JSON（★ 可完全覆盖内置表）  默认 空
"""
import json
import os
import sys
from pathlib import Path

CONFIG_NAME = 'session-memory.config.json'

DEFAULT = {
    'docs_dir': 'docs',
    'spec': 'DESIGN-SPEC.md',
    'progress': 'DESIGN-SPEC-PROGRESS.md',
    'index': 'SESSION-INDEX.md',
    'ledger': 'PENDING-LEDGER.md',
    'input': '_both.txt',
    'tags': '',
}


def _load_json(p):
    try:
        # utf-8-sig：★ 容忍 BOM（手工编辑过的 json 常带 BOM）
        return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except Exception:
        return {}


def load(argv=None):
    """解析配置。返回 `(conf, argv_已去掉 --config)`。"""
    argv = list(sys.argv[1:] if argv is None else argv)

    path = ''
    if '--config' in argv:
        i = argv.index('--config')
        if i + 1 < len(argv):
            path = argv[i + 1]
        del argv[i:i + 2]

    conf = dict(DEFAULT)

    if not path:
        auto = Path.cwd() / CONFIG_NAME
        if auto.is_file():
            path = str(auto)
    if not path:
        path = os.environ.get('SESSION_MEMORY_CONFIG') or ''
    if path:
        conf.update({k: v for k, v in _load_json(path).items()
                     if v not in (None, '')})

    for k in DEFAULT:
        env = os.environ.get('SESSION_MEMORY_' + k.upper())
        if env:
            conf[k] = env

    return conf, argv


def doc_path(conf, key):
    """`docs_dir` 下的文档相对路径（`docs_dir` 为空则只返回文件名）。"""
    d = conf.get('docs_dir') or ''
    return str(Path(d) / conf[key]) if d else conf[key]


def load_tags(conf, explicit=''):
    """分类关键词表：★ 可**完全覆盖**内置表。

    JSON 形状：`{"标签": ["关键词", ...], ...}`（★ 标签可有交集）。
    返回 `None` ⇒ 调用方用内置表（★ 不静默换表：调用方会打印实际用的来源）。
    """
    p = (explicit or conf.get('tags')
         or os.environ.get('SESSION_MEMORY_TAGS') or '')
    if p and Path(p).is_file():
        data = _load_json(p)
        if isinstance(data, dict) and data:
            out = {}
            for k, v in data.items():
                if isinstance(v, (list, tuple)):
                    out[str(k)] = tuple(str(x) for x in v)
                else:
                    out[str(k)] = (str(v),)
            return out
    return None
