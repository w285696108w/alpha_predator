# AlphaPredator - GitHub 发布指南

## 网络限制说明

当前机器无法直接访问 GitHub（DNS/网络层面封锁）。以下提供两种发布方式：

---

## 方式一：手动上传到 GitHub（推荐）

### 步骤 1：打包项目

项目已打包为 `alpha_predator.zip`，包含所有源码文件。

### 步骤 2：在 GitHub 创建仓库

1. 打开 https://github.com/new
2. 填写仓库名称：`alpha_predator`
3. 选择 Public（公开）或 Private
4. **不要**勾选 "Initialize this repository with a README"
5. 点击 Create repository
6. 在 "…or push an existing repository from the command line" 部分，复制提供的命令

### 步骤 3：本地推送（需要在一台能访问 GitHub 的机器上）

在一台可以访问 GitHub 的机器上：

```bash
# 1. 解压
unzip alpha_predator.zip
cd alpha_predator

# 2. 初始化 Git（如果是手动下载的）
git init
git add .
git commit -m "AlphaPredator: 散户反制大资本量化系统 v1.0"

# 3. 关联远程仓库（将 YOUR_USERNAME 替换为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/alpha_predator.git
git branch -M main

# 4. 推送
git push -u origin main
```

---

## 方式二：通过 Gitee 镜像（当前机器可直接访问）

Gitee 可以免费创建仓库，且可以一键导入 GitHub 仓库：

1. 打开 https://gitee.com/new
2. 创建仓库 `alpha_predator`
3. 创建后，在仓库设置中可选择"从 GitHub 导入"
4. 导入完成后，在 Gitee 仓库页面可一键推送到 GitHub

---

## 方式三：使用 GitHub CLI（需要在能访问 GitHub 的机器）

```bash
# 安装 gh（如果还没有）
winget install GitHub.cli

# 认证
gh auth login

# 创建仓库并推送
gh repo create alpha_predator --public --push
git clone https://github.com/YOUR_USERNAME/alpha_predator.git
# 复制源码进去后
git add . && git commit && git push
```

---

## 验证

推送成功后，访问：
- GitHub: https://github.com/YOUR_USERNAME/alpha_predator
- GitHub Actions: https://github.com/YOUR_USERNAME/alpha_predator/actions

CI 应自动运行回测，结果应显示：
- Total trades: 2-3
- Sharpe ratio: ~0.5
- Profitable: 4/5

---

## 项目内容

```
alpha_predator/
├── README.md              # 中文说明（主）
├── README_EN.md           # 英文说明
├── LICENSE                # MIT 许可证
├── .gitignore
├── requirements.txt
├── .github/workflows/ci.yml  # GitHub Actions 自动回测
├── config/
│   └── settings.py        # 全局配置
├── data/
│   ├── __init__.py
│   ├── fetcher.py         # 数据获取（AKShare + 模拟）
│   ├── institutional.py   # 机构资金追踪
│   └── alternative.py     # NLP 舆情
├── signals/
│   ├── __init__.py
│   ├── alpha_signals.py   # Alpha 信号生成
│   ├── regime_detector.py  # 市场状态检测
│   └── anti_quant.py      # 反量化机制
├── strategies/
│   ├── __init__.py
│   ├── base.py
│   ├── momentum_breakout.py
│   └── adaptive.py
├── risk/
│   ├── __init__.py
│   └── position_manager.py
├── backtest/
│   ├── __init__.py
│   └── engine.py          # 纯 Python 回测引擎
├── main.py                # 主入口（实盘/模拟盘）
└── run_backtest.py        # 回测入口
```
