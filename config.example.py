# -*- coding: utf-8 -*-
"""
配置模板：复制成 config.py 再改。
config.py 不要提交到仓库（.gitignore 里已经排除了）。
"""

# ---- 被检查的那台机器 ----
HOST = "1.2.3.4"            # 服务器 IP 或域名
USER = "ubuntu"             # 登录用户
KEY = "id_ed25519"          # 私钥文件名（和本文件同目录），或写绝对路径
PORT = 22

# ---- 那台机器上的项目 ----
SERVICE = "myagent"                 # systemd 服务名
LOG = "/opt/myagent/agent.log"      # 日志文件
DATA = "/opt/myagent/data"          # 数据目录（放 *.md、chat_history.jsonl、logs/）
