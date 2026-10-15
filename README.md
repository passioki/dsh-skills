# dsh-skills

DSH（DeepSeek Harness）**用户级技能**的集中仓库 —— 两台机器之间同步技能用。

> ★ **为什么单独建一个仓库**：技能放在 DSH 的配置目录（`%DSH_HOME%\skills\`）里，
> **不属于任何项目仓库**（不属于 `backend\` / `frontend\`），所以项目 `git pull` 带不过来。

---

## 一、仓库结构

```
dsh-skills\
├── README.md                     ← 本文件
├── install.bat                   ← ★ 推荐入口：双击 / 命令行都可，自动绕过执行策略
├── install.ps1                   ← 真正的安装脚本（★ 带 UTF-8 BOM）
├── .gitattributes                ← 统一 LF（本仓库所有文件都是 LF）
└── skills\
    └── session-memory\           ← 一个技能 = 一个目录
        ├── SKILL.md              ← ★ 必需：正文 + YAML 头部（name / description）
        └── scripts\
            ├── extract.py        ← 从 DSH 会话 jsonl 导出双向纯文本
            ├── seg.ps1           ← 取指定时间段的完整对话
            ├── index_gen.py      ← 生成 SESSION-INDEX.md
            └── prog_gen.py       ← 生成 DESIGN-SPEC-PROGRESS.md
```

★ 分支：本仓库只有 `main` 一个分支（技能仓库不需要"dev 开发 / main 稳定"那一套）。

---

## 二、另一台机器：首次安装（3 步）

```powershell
# ① 克隆到任意位置（建议放在开发工作区旁边）
cd D:\
git clone https://github.com/<你的账号>/dsh-skills.git

# ② 确认 DSH 配置根
echo $env:DSH_HOME          # 有输出就用它；为空则默认 %USERPROFILE%\.dsh

# ③ 一键安装（★ 推荐用 install.bat —— 它自带 -ExecutionPolicy Bypass）
cd D:\dsh-skills
.\install.bat
```

★ 脚本会打印自检结果（应列出 `SKILL.md`），**不需要重启 DSH**（DSH 会热加载技能目录）。

★ 不想用 `.bat` 的话，也可以显式绕过执行策略：
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```
（直接 `.\install.ps1` 可能报 **"not digitally signed"** —— 那是执行策略，不是脚本坏了）

---

## 三、日常同步

| 模式 | 怎么装 | 以后怎么同步 |
|---|---|---|
| ★ **Junction（默认）** | `.\install.ps1` | ★ **只 `git pull` 就行**（联接指向仓库，文件立刻生效） |
| 复制 | `.\install.ps1 -Copy` | `git pull` 后 **再跑一次** `.\install.ps1 -Copy` |

```powershell
cd D:\dsh-skills
git pull
```

★ Junction 模式不需要管理员权限；DSH 目录里看到的是一个"目录联接"（资源管理器里带快捷方式箭头）。

---

## 四、新增一个技能

```
① 在 skills\ 下建目录：skills\<技能名>\
② 放 SKILL.md（★ 开头必须有 YAML 头部）：
       ---
       name: <技能名>            ← 必须与目录名一致
       description: <一句话说明，DSH 用它在会话目录里介绍该技能>
       ---
       正文…
③ 需要脚本就放 skills\<技能名>\scripts\ 下
④ 提交 + 推送 ⇒ 另一台 git pull（Junction 模式下立即生效）
```

★ 也可以用现成的机器技能做模板：先把 `%DSH_HOME%\skills\<技能名>\` 拷进 `skills\`，再提交。

---

## 五、注意事项

| # | 事项 |
|---|---|
| **1** | ★ 技能**只能**放在这两个被扫描的根下：`%DSH_HOME%\skills\`（默认 `~\.dsh\skills\`）或 `~\.agents\skills\`。**放进 `backend\` / `frontend\` 是没用的**（DSH 不扫描那里） |
| **2** | ★ **别把 `SKILL.md` 直接丢在 `skills\` 根下** —— 必须是一个目录，里面放 `SKILL.md` |
| **3** | ★ `SKILL.md` 的 YAML 头部的 `name` 必须与目录名一致 |
| **4** | 依赖：**Python 3**（`extract.py` / `index_gen.py` / `prog_gen.py`，只用标准库，不需要 pip 装包）· **PowerShell**（`seg.ps1`） |
| **5** | `session-memory` 的输入是 DSH 导出的会话包（`dsh-session-*.zip` → `session.v4.jsonl`），**由使用者自己导出**，不在本仓库里 |
| **6** | ★ 脚本 `seg.ps1` 的 `-File` 默认值是 `D:\OAS-dev\_both.txt`（仅是默认参数，用 `-File` 覆盖即可，**不用改脚本**） |
| **7** | 随 DSH 安装包发布的技能（例如 `diagnose-windows-sandbox-acl`）**不在本仓库**，装了 DSH 就自带 |
| **8** | ★★ **`install.ps1` 必须保留 UTF-8 BOM**（文件开头 `EF BB BF`）—— Windows PowerShell 5.1 读 `.ps1` 时**不认"无 BOM 的 UTF-8"**，会把中文按 GBK 解码 ⇒ 脚本**直接解析失败**（实测踩过：`复制` 变成 `澶嶅埗`）。★ 用 VS Code 编辑默认会保留 BOM；若你用过别的编辑器，`git diff` 里看一下 BOM 是否还在 |
| **9** | ★ **执行策略**：本机 `CurrentUser = RemoteSigned`，实测直接 `.\install.ps1` 会报 **"not digitally signed"** ⇒ 用 **`install.bat`**（或 `-ExecutionPolicy Bypass`）。★ 不要为了这个去改全局执行策略 |
| **10** | ★ 删除联接**只能**用 `cmd /c rmdir "<路径>"`。★ **不要**用 `Remove-Item -Recurse`：旧版 PowerShell 会顺着联接**删掉链接指向的真实内容**（`install.ps1` 里已经规避了这一点） |

---

## 六、回退

`install.ps1` **从不删除**你的技能目录 —— 目标已存在时只会改名备份：

```
%DSH_HOME%\skills\<技能名>.bak-20261015-123456\
```

要回退：删掉联接（`cmd /c rmdir "<技能名>"`），再把备份目录改回原名即可。
