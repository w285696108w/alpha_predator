#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

"""
AlphaPredator - GitHub 一键发布脚本

使用方法:
    python github_push.py YOUR_GITHUB_TOKEN

创建 GitHub PAT:
    https://github.com/settings/tokens/new
    勾选: repo (全部), admin:public_repo (用于创建公开仓库)
    复制 token，粘贴到上面命令中

这个脚本会:
1. 通过 GitHub API 创建仓库 alpha_predator
2. 通过 GitHub API 上传所有源码文件
3. 打印最终仓库地址
"""
import urllib.request, urllib.error, ssl, json, os, sys, base64

# ─── 配置 ───
GITHUB_TOKEN = None          # 将在运行时从命令行参数获取
REPO_NAME = "alpha_predator"
GITHUB_USER = None           # 将从 API 自动获取

# ─── 网络 ───
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def api(url, method='GET', data=None, accept='application/json'):
    """GitHub API 请求"""
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': accept,
        'User-Agent': 'AlphaPredator-Push/1.0',
    })
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=30)
        return json.loads(r.read()) if r.status != 204 else None
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read())
        except:
            err = e.read().decode()[:200]
        return {'__http_error__': e.code, '__body__': err}

# ─── 步骤 1: 验证 token，获取用户名 ───
def step1_validate():
    global GITHUB_USER
    print('[1/5] 验证 GitHub Token...')
    result = api('https://api.github.com/user')
    if '__http_error__' in result:
        print(f'    [FAIL] Token 验证失败 (HTTP {result["__http_error__"]}): {result}')
        return False
    GITHUB_USER = result['login']
    print(f'    [OK] Token 有效！用户: {result.get("name","")} (@{GITHUB_USER})')
    return True

# ─── 步骤 2: 创建仓库 ───
def step2_create_repo():
    print(f'[2/5] 创建仓库 {REPO_NAME}...')
    payload = {
        'name': REPO_NAME,
        'description': '散户反制大资本量化系统 | Retail Anti-Quant Trading System',
        'private': False,
        'auto_init': False,
        'has_wiki': False,
        'has_projects': False,
    }
    result = api('https://api.github.com/user/repos', method='POST', data=payload)
    if '__http_error__' in result:
        code = result['__http_error__']
        body = result['__body__']
        if code == 422:  # 仓库已存在
            print(f'    [WARN]  仓库已存在，跳过创建')
            return True
        print(f'    [FAIL] 创建失败 (HTTP {code}): {body}')
        return False
    print(f'    [OK] 仓库创建成功: {result.get("html_url","")}')
    return True

# ─── 步骤 3: 上传文件 ───
def step3_upload_files():
    print('[3/5] 上传源码文件...')
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # 上级目录的 alpha_predator 子目录
    project_dir = os.path.join(os.path.dirname(base_dir), 'alpha_predator')
    if not os.path.exists(project_dir):
        project_dir = base_dir  # 本身就在 alpha_predator 目录里

    file_count = 0
    for root, dirs, files in os.walk(project_dir):
        # 跳过 .git 等目录
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.github']]
        for file in files:
            if file.endswith('.pyc'):
                continue
            filepath = os.path.join(root, file)
            arcname = os.path.relpath(filepath, project_dir).replace(os.sep, '/')
            # 跳过 .github 目录下的文件（会单独处理）
            if arcname.startswith('.github/'):
                continue
            with open(filepath, 'rb') as f:
                content = base64.b64encode(f.read()).decode()
            url = f'https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{arcname}'
            payload = {
                'message': f'Add {arcname}',
                'content': content,
            }
            # 先查当前 SHA（如果文件已存在）
            existing = api(url)
            if existing and '__http_error__' not in existing:
                payload['sha'] = existing.get('sha')
            result = api(url, method='PUT', data=payload, accept='application/vnd.github.v3+json')
            if '__http_error__' in result and result['__http_error__'] not in (201, 200):
                print(f'    [WARN]  上传失败 {arcname}: {result}')
            else:
                file_count += 1
    print(f'    [OK] 上传了 {file_count} 个文件')
    return True

# ─── 步骤 4: 上传 GitHub Actions ───
def step4_upload_actions():
    print('[4/5] 上传 GitHub Actions 工作流...')
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(os.path.dirname(base_dir), 'alpha_predator')
    wf_path = os.path.join(project_dir, '.github', 'workflows', 'ci.yml')
    if not os.path.exists(wf_path):
        print('    [WARN]  ci.yml 不存在，跳过')
        return True
    with open(wf_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode()
    url = f'https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/.github/workflows/ci.yml'
    payload = {'message': 'Add CI workflow', 'content': content}
    existing = api(url)
    if existing and '__http_error__' not in existing:
        payload['sha'] = existing.get('sha')
    result = api(url, method='PUT', data=payload)
    if '__http_error__' in result and result['__http_error__'] not in (201, 200):
        print(f'    [WARN]  上传 ci.yml 失败: {result}')
    else:
        print('    [OK] CI 工作流上传成功')
    return True

# ─── 步骤 5: 验证 ───
def step5_verify():
    print('[5/5] 验证仓库...')
    url = f'https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}'
    result = api(url)
    if '__http_error__' in result:
        print(f'    [FAIL] 验证失败: {result}')
        return False
    html_url = result.get('html_url', '')
    clone_url = result.get('clone_url', '')
    print('')
    print('=' * 60)
    print('[SUCCESS] 发布成功！')
    print(f'   仓库: {html_url}')
    print(f'   CI:   {html_url}/actions')
    print(f'   Clone: {clone_url}')
    print('=' * 60)
    return True

# ─── 主流程 ───
def main():
    global GITHUB_TOKEN

    if len(sys.argv) < 2:
        print('用法: python github_push.py YOUR_GITHUB_TOKEN')
        print()
        print('创建 Token: https://github.com/settings/tokens/new')
        print('需要的权限: repo (全部) | admin:public_repo')
        sys.exit(1)

    GITHUB_TOKEN = sys.argv[1].strip()

    print('=' * 60)
    print('AlphaPredator GitHub 发布脚本')
    print('=' * 60)
    print()

    if not step1_validate(): sys.exit(1)
    if not step2_create_repo(): sys.exit(1)
    if not step3_upload_files(): sys.exit(1)
    if not step4_upload_actions(): sys.exit(1)
    if not step5_verify(): sys.exit(1)

if __name__ == '__main__':
    main()
