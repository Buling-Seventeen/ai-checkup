# -*- coding: utf-8 -*-
"""在远程机器上跑一条命令：python _ssh.py "df -h /"

配置在 config.py 里（HOST / USER / KEY / PORT）。
"""
import os
import sys

import paramiko

import config as cfg

BASE = os.path.dirname(os.path.abspath(__file__))
KEY = cfg.KEY if os.path.isabs(cfg.KEY) else os.path.join(BASE, cfg.KEY)

cmd = " ".join(sys.argv[1:]) or "echo hi"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(getattr(cfg, "HOST"), getattr(cfg, "PORT", 22), cfg.USER,
          pkey=paramiko.Ed25519Key.from_private_key_file(KEY),
          timeout=30, allow_agent=False, look_for_keys=False)
_, out, err = c.exec_command(cmd, timeout=120)
print(out.read().decode("utf-8", "ignore"))
e = err.read().decode("utf-8", "ignore").strip()
if e:
    print("[stderr]", e[-1200:])
c.close()
