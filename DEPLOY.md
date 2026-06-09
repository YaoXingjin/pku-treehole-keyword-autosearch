# PKU CLab 云主机部署

本文件说明如何把项目部署到 PKU CLab 云主机并每天定时执行。CLab 云主机创建和 SSH 连接方式请先阅读官方文档：[CLab 快速上手](https://clab.pku.edu.cn/docs/getting-started/introduction)。

## 前提

- 已有一台 CLab 云主机。推荐使用 `rocky`。 
- 云主机位于共享网络 `pku` 或 `pku-new`，可以访问北大校内服务。
- 本地可以通过 SSH 登录云主机。
- 已经准备好 `config_private.py`，但不要把它提交到 Git。

下面示例使用占位符，请按自己的环境替换：

```text
<remote_user>      云主机用户名，例如 rocky / ubuntu / debian
<remote_host>      云主机 IP，例如 10.129.x.x
<project_dir>      远程项目目录，例如 /home/<remote_user>/projects/pku-treehole-keyword-autosearch
<identity_file>    SSH 私钥路径，可选
```

## 1. 上传代码

在云主机上创建项目目录：

```bash
mkdir -p /home/<remote_user>
```

推荐部署到 `~/pku-treehole-keyword-autosearch`，也可以选择任意目录。用 GitHub 更新代码：

```bash
cd /home/<remote_user>
git clone https://github.com/YaoXingjin/pku-treehole-keyword-autosearch.git pku-treehole-keyword-autosearch
```

如果云主机暂时不能访问 GitHub，也可以从本地打包上传，但不要把 `config_private.py`、状态文件、日志、cookie 一起打包。

## 2. 上传私有配置

`config_private.py` 包含账号、密码、关键词和 MeoW 昵称，不应进入公开仓库。请手动上传到远程项目目录：

```bash
scp config_private.py <remote_user>@<remote_host>:<project_dir>/config_private.py
```

设置权限：

```bash
cd <project_dir>
chmod 600 config_private.py
```

只需要检查文件是否存在和权限是否正确，不要在日志或终端里打印配置内容。

## 3. 安装依赖

```bash
cd <project_dir>
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
chmod +x scripts/*.sh
```

如果云主机没有外网，先执行下一节的北大网关登录，或临时使用可用代理安装依赖。

## 4. 登录北大网关

CLab 云主机访问互联网前通常需要登录北大网关。官方文档中也说明云主机和普通设备一样，需要连接网关才能访问互联网。

可以参考 CLab 官方文档中的说明登录网关，也可使用本项目提供的脚本：

```bash
python3 scripts/its_network_login.py
```

改脚本按以下顺序读取凭据：

1. `ITS_USERNAME` / `ITS_PASSWORD`
2. `TREEHOLE_USERNAME` / `TREEHOLE_PASSWORD`
3. `config_private.py` 中的 `USERNAME` / `PASSWORD`
4. 如果是交互终端且以上都没有，则手动输入

手动测试：

```bash
cd <project_dir>
python3 scripts/its_network_login.py
python3 search_keyword.py --test-push
```

如果 `ITS authenticated IP` 显示的是云主机 IP，并且 MeoW 测试推送成功，说明外网和推送链路正常。

## 5. 部署前检查

```bash
cd <project_dir>
PROJECT_DIR=<project_dir> scripts/check_deploy_ready.sh
```

检查内容包括：

- `config_private.py` 是否存在
- `config_private.py` 权限是否为 `600`
- Python 脚本是否能编译

该检查不会读取配置内容。

## 6. 启用 systemd user timer

先写入项目目录环境文件。这里的 `PROJECT_DIR` 可以是任意实际部署路径：

```bash
mkdir -p ~/.config/pku-treehole-keyword-autosearch
cat > ~/.config/pku-treehole-keyword-autosearch/env <<'EOF'
PROJECT_DIR=/home/<remote_user>/pku-treehole-keyword-autosearch
MEOW_NICKNAME=<your_meow_nickname>
EOF
```

`MEOW_NICKNAME` 也可以只写在 `config_private.py` 中；但更建议同时写入这个 systemd 环境文件。当 `config_private.py` 缺失、路径写错或 Python 环境尚未安装完整时，失败提醒也更有机会发到手机。

启动提醒默认关闭，避免每天定时运行都推送“任务启动”消息。部署调试时如需确认 timer 是否触发，可以临时加入：

```bash
MEOW_STARTUP_NOTIFY=1
```

复制 service 和 timer：

```bash
mkdir -p ~/.config/systemd/user
cp deploy/treehole-search.service ~/.config/systemd/user/
cp deploy/treehole-search.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now treehole-search.timer
```

默认 timer 使用 UTC 02:00，即北京时间 10:00：

```ini
OnCalendar=*-*-* 02:00:00
```

查看状态：

```bash
systemctl --user status treehole-search.timer
systemctl --user list-timers --all | grep treehole
```

手动触发一次：

```bash
systemctl --user start treehole-search.service
```

查看日志：

```bash
tail -n 100 logs/treehole-search.log
```

如果设置了 `MEOW_STARTUP_NOTIFY=1`，手动触发后，脚本启动时会尽量发送标题为 `树洞定时任务启动` 的 MeoW 提醒。默认不发送启动提醒。若执行失败，脚本会尽量发送标题为 `树洞定时任务失败` 的 MeoW 提醒。失败提醒正文会包含失败原因、发生时间、主机名、项目目录和日志路径。

## 7. 检查运行状态

登录云主机后，先确认 systemd timer 是否启用、下一次什么时候运行：

```bash
systemctl --user status treehole-search.timer
systemctl --user list-timers --all | grep treehole
```

再看 service 最近一次执行结果：

```bash
systemctl --user status treehole-search.service
```

读取项目目录环境文件，确认 `PROJECT_DIR` 指向哪里。不要在这里放账号密码；如果写了 `MEOW_NICKNAME`，它只用于失败提醒。

```bash
cat ~/.config/pku-treehole-keyword-autosearch/env
```

进入项目目录后看最近日志：

```bash
cd <project_dir>
tail -n 100 logs/treehole-search.log
```

只检查私有配置是否存在和权限是否正确，不要打印 `config_private.py` 内容：

```bash
test -f config_private.py && echo "config_private.py exists"
stat -c "%a %n" config_private.py
```

如果想立刻跑一次完整定时流程：

```bash
systemctl --user start treehole-search.service
tail -n 100 logs/treehole-search.log
```

如果 timer 没有按预期出现，重新加载并启动：

```bash
systemctl --user daemon-reload
systemctl --user enable --now treehole-search.timer
systemctl --user list-timers --all | grep treehole
```

默认配置下，`treehole-search.timer` 每天 UTC 02:00 运行，也就是北京时间 10:00。可以用下面命令确认 timer 文件里的时间：

```bash
grep OnCalendar ~/.config/systemd/user/treehole-search.timer
```

## 8. 运行逻辑

`scripts/run_treehole_search.sh` 会：

1. 检查 `PROJECT_DIR` 指向的项目目录是否存在。
2. 创建 `logs/` 和 `state/`。
3. 如果设置了 `MEOW_STARTUP_NOTIFY=1`，发送 `树洞定时任务启动` MeoW 提醒；默认跳过启动提醒。
4. 检查是否存在可运行且安装了 `requests` 的 Python。
5. 检查 `config_private.py` 是否存在。
6. 先登录北大网关。
7. 再以非交互模式运行树洞搜索。

以下失败会尽量通过 MeoW 推送提醒：

- `PROJECT_DIR` 不存在。
- 找不到可用 Python，或 Python 没有安装 `requests`。
- 缺少 `config_private.py`。
- 北大网关登录脚本异常退出。
- `search_keyword.py --non-interactive` 异常退出，包括树洞登录态失效、令牌验证、搜索接口异常、配置错误或推送失败。

如果树洞登录态失效并需要 PKU Helper 令牌，`search_keyword.py` 会发送专门的令牌验证提醒；外层定时入口检测到该提醒已经发送后，只记录日志，不再重复发送通用失败提醒。

失败提醒依赖 MeoW 可达，且至少能从 `MEOW_NICKNAME` 环境变量或 `config_private.py` 中取得 MeoW 昵称。对于“找不到 Python”或“缺少 `config_private.py`”这类早期错误，最好在 systemd 环境文件里设置 `MEOW_NICKNAME`。

## 9. GitHub 更新

后续更新代码可以在云主机上执行：

```bash
cd <project_dir>
git pull
systemctl --user daemon-reload
systemctl --user restart treehole-search.timer
```

如果云主机访问 GitHub 需要代理，可以临时设置反向转发端口以使用本地代理软件，例如：

```bash
export HTTP_PROXY=http://127.0.0.1:<proxy_port>
export HTTPS_PROXY=http://127.0.0.1:<proxy_port>
```

树洞和 IAAA 域名建议保持直连：

```bash
export NO_PROXY=localhost,127.0.0.1,::1,treehole.pku.edu.cn,iaaa.pku.edu.cn
```
