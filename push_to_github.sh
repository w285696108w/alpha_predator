#!/usr/bin/env bash
# AlphaPredator 一键推送到 GitHub
# 用法: bash push_to_github.sh YOUR_GITHUB_USERNAME
#
# 要求: git + gh CLI 已安装，且已登录 GitHub
#   gh auth login

set -e

if [ -z "$1" ]; then
    echo "用法: bash push_to_github.sh YOUR_GITHUB_USERNAME"
    exit 1
fi

GITHUB_USER="$1"
REPO_NAME="alpha_predator"
ZIP_URL="https://github.com/YOUR_USERNAME/alpha_predator/archive/refs/heads/main.zip"

echo "============================================"
echo "AlphaPredator GitHub Push Script"
echo "============================================"

# 检查工具
command -v git >/dev/null 2>&1 || { echo "需要安装 git: https://git-scm.com"; exit 1; }

# 如果没有 gh，使用 git 直接推送
if command -v gh >/dev/null 2>&1; then
    echo "[1/4] GitHub CLI (gh) 已安装"
    USE_GH=1
else
    echo "[1/4] gh 未安装，使用 git 直接推送"
    USE_GH=0
fi

# 创建临时目录
TEMP_DIR=$(mktemp -d)
echo "[2/4] 工作目录: $TEMP_DIR"
cd "$TEMP_DIR"

# 解压（如果用户提供的是 ZIP）
if [ -f "$HOME/Downloads/alpha_predator.zip" ]; then
    echo "找到 ZIP 文件，解压中..."
    unzip -q "$HOME/Downloads/alpha_predator.zip"
    mv alpha_predator-* alpha_predator 2>/dev/null || true
fi

# 如果目录为空，创建并初始化
if [ ! -f "alpha_predator/README.md" ]; then
    echo "错误: 找不到项目文件。请确保 alpha_predator 目录或 ZIP 文件在当前目录"
    exit 1
fi

cd alpha_predator

# Git 初始化
if [ ! -d .git ]; then
    echo "[3/4] 初始化 Git 仓库..."
    git init
    git add .
    git commit -m "AlphaPredator: 散户反制大资本量化系统 v1.0"
else
    echo "[3/4] Git 仓库已存在，更新中..."
    git add .
    git commit -m "Update $(date '+%Y-%m-%d')" || true
fi

# 关联并推送
REMOTE_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"

if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi

git branch -M main
echo "[4/4] 推送到 GitHub..."
git push -u origin main --force

echo ""
echo "============================================"
echo "SUCCESS! 仓库地址:"
echo "  https://github.com/${GITHUB_USER}/${REPO_NAME}"
echo ""
echo "查看 GitHub Actions:"
echo "  https://github.com/${GITHUB_USER}/${REPO_NAME}/actions"
echo "============================================"

# 清理
cd /
rm -rf "$TEMP_DIR"
