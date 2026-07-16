<div align="center">

[English](README.md) · [中文](README.zh.md) · [Русский](README.ru.md)

![scratrace](assets/scratrace.png)

# scratrace

**一款通过用户名、电子邮件、电话号码和全名查找人物的 OSINT 工具。**

链接干净。零误报。界面精美。多语言支持。

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
| 📧 `email`         | 按电子邮件搜索                              |
| 📱 `number_phone`  | 按电话号码搜索                              |
| 👤 `full_name`     | 按姓名搜索                                  |

---

## ⚡ 我们的优势

> 为什么选择 `scratrace`，而不是又一个 `sherlock` 分叉？

### 1. 干净的链接，没有误报

大多数 OSINT 工具（包括热门工具）只要站点返回**任何**响应就认为「找到了」——
哪怕是 `404` 或「用户不存在」页面。我们通过双重请求验证每个站点：

- 代入一个**常见**用户名（`news`、`user`、`admin`）；
- 代入一个**故意随机**的 `kljwwdlkjadkljakdl`。

如果响应码**相同**——说明站点在撒谎（总是返回 `200`）→ `type_url=None`，
该链接不算可用。如果响应码**不同**——说明站点诚实 → 记录真实响应码
（`type_url=200`），然后才使用它。

```
username=news      → 200
username=kljwwd... → 404   ✅ 诚实，type_url=200

username=news      → 200
username=kljwwd... → 200   ❌ 撒谎，type_url=None（已剔除）
```

目录目前还不算最大，但**其中每个链接都是最新且经过验证的**。

### 2. 精美、友好的界面

渐变菜单、带百分比和实时结果列表的进度条、带强调色的分类。全部基于
[`rich`](https://github.com/Textualize/rich) 构建。

<div align="center">

![scratrace 在终端中的样子](assets/terminal.png)

</div>

### 3. 多语言翻译

内置 i18n 系统。目前支持：

| 语言       | 代码 |
| ---------- | ---- |
| 🇷🇺 Русский | `ru` |
| 🇬🇧 English | `en` |
| 🇨🇳 中文    | `cn` |

在 **Settings** 菜单中切换 → 选择语言。

---

## 🚀 安装

最快的方式是直接从 GitHub 安装：

```bash
pip install git+https://github.com/0xScodyx/scratrace.git
```

或安装指定标签的版本：

```bash
pip install git+https://github.com/0xScodyx/scratrace.git@v0.1.0
```

用于开发（可编辑模式）：

```bash
git clone https://github.com/0xScodyx/scratrace.git
cd scratrace
pip install -e .
```

依赖：`aiohttp`、`rich`、`pytest`、`pytest-xdist`。

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

---

## 🧪 测试与目录清理

失效站点通过 `pytest` 检测并自动清除：

```bash
pytest tests/test_sites.py -n auto     # 将失效站点写入 .dead_sites.json
python tests/cut_sites.py              # 从 sites.py 中删除它们
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

## 📜 许可证

MIT © scratrace contributors
