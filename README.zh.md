<div align="center">

[English](README.md) · [中文](README.zh.md) · [Русский](README.ru.md)

![scratrace](assets/scratrace.png)

# scratrace

**一款通过用户名、电子邮件、电话号码和全名查找人物的 OSINT 工具。**

链接干净。Playwright 驱动。多语言支持。

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)]()

</div>

---

## 🔍 这是什么

`scratrace` 是一款命令行 OSINT 扫描器，它会遍历站点目录，根据给定的标识符查找
用户资料。与大多数同类工具不同，我们**绝不随意报告命中**：目录中的每个链接都经过
真实性验证，会撒谎的站点将被标记并剔除。

### 支持的搜索类型

| 类型               | 说明                                        |
| ------------------ | ------------------------------------------- |
| 🧑 `username`      | 在社交网络、论坛、开发平台等按昵称搜索       |
| 📧 `email`         | 按电子邮件搜索 · _即将推出_                   |
| 📱 `number_phone`  | 按电话号码搜索 · _即将推出_                  |
| 👤 `full_name`     | 按姓名搜索 · _即将推出_                      |

---

## ⚡ 我们的优势

> 受 [Maigret](https://github.com/soxoj/maigret) 启发——拥有 3000+ 站点和双重验证机制的成熟 OSINT 工具。
> 我们目标相同，但选择了不同的技术路径。

### 1. SQLite 替代 JSON——更轻量、有类型

大多数 OSINT 工具将 3000+ 站点存在 **4.4 万行的 JSON 文件**（`data.json`，1.4MB）中。
没有 schema，全量加载到内存，无法索引。

我们使用 **SQLite**（`SiteRegistry.db`，536KB）。列有类型（`int`、`str`、`JSON`、`bool`），
支持 `SELECT`、`UPDATE`、`DELETE`，数据库再大也保持快速。

### 2. Playwright 处理 SPA 和反爬站点

我们通过 Playwright 运行**真实浏览器脚本**，支持 TikTok、Replit、Weebly、Wix、Fiverr 等。

### 3. 内置搜索

除了站点目录，还会自动通过 Playwright 在 DuckDuckGo 搜索用户名，
在「Other Info」类别中展示网络上的公开信息。
无需 API 密钥，无需验证码。

### 4. 精美、友好的界面

渐变菜单、带百分比和实时结果列表的进度条、带强调色的分类。全部基于
[`rich`](https://github.com/Textualize/rich) 构建。

<div align="center">

![scratrace 在终端中的样子](assets/terminal.png)

</div>

### 5. 多语言翻译

内置 i18n 系统。目前支持：

| 语言       | 代码 |
| ---------- | ---- |
| 🇷🇺 Русский | `ru` |
| 🇬🇧 English | `en` |
| 🇨🇳 中文    | `cn` |

在 **Settings** 菜单中切换 → 选择语言。

### 6. 速度

pyscratrace 速度很快。一次典型的用户名搜索大约需要 15-30 秒。

## 🚀 安装

> **许可变更：** scratrace 此前使用 GPL v3 许可证。从 v0.2.2 起改为 MIT 许可证。

```bash
pip install git+https://github.com/0xScodyx/scratrace.git
```

或安装指定标签的版本：

```bash
pip install git+https://github.com/0xScodyx/scratrace.git@v0.2.2
```

### 浏览器检测（可选）

需要 Playwright 浏览器检测和 DuckDuckGo 搜索时，安装额外依赖并下载浏览器：

```bash
pip install "scratrace[browser] @ git+https://github.com/0xScodyx/scratrace.git"
playwright install chromium
```

如果已安装基础包，之后想添加浏览器支持：

```bash
pip install playwright playwright-stealth
playwright install chromium
```

### 开发模式（可编辑安装）

```bash
git clone https://github.com/0xScodyx/scratrace.git
cd scratrace
pip install -e .
```

## 💻 使用

```bash
pyscratrace          # 交互式菜单
```

选择搜索类型（`username` / `email` / `phone` / `full_name`），输入值，
即可查看实时进度。完成后按 `Enter`。

### 编程调用

```python
from scratrace.osint import UserName

results = UserName("scodyx").check_all()
# -> {'social': [...], 'forums': [...], 'gaming': [...], ...}
```

### 查看日志

```bash
scratrace-log        # 查看最新搜索日志
```

---

## 🧪 测试

```bash
pytest
```

---

## 🗂 结构

```
src/scratrace/
├── app.py            # 交互式菜单 (rich)
├── ui.py             # 渐变、表格、进度
├── i18n.py / lang.json
├── banner.py
└── osint/
    ├── sites.py      # 站点注册表 (Sites 对象)
    ├── username.py   # 用户名检查
    ├── email.py
    ├── number_phone.py
    └── full_name.py
tests/
├── test_sites.py     # 可达性检查（请勿改动！）
├── conftest.py       # 失效站点收集
└── cut_sites.py      # 自动删除
```

---

## 👥 贡献者

感谢所有让 `scratrace` 更干净、更精准的人：

<!-- contrib.rocks: 贡献者头像通过 GitHub API 自动拉取 -->
<a href="https://github.com/0xScodyx/scratrace/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=0xScodyx/scratrace" />
</a>

> 想出现在这里？向 `sites.py` 添加站点或改进检查逻辑——欢迎提交 PR！

---

## 🤝 贡献指南

所有 PR 和提交请发往 `dev` 分支。`main` 分支仅用于稳定发布。不要直接合并到 `main`——请向 `dev` 发起 PR。

---

## 📜 许可证

MIT © scratrace contributors
