# 北大树洞关键词定时检索

在 PKU CLab 云主机部署脚本**定时检索含有特定关键词的[北大树洞](https://treehole.pku.edu.cn/ch/web/pc/index)**，并在发现新增帖子时**推送到移动设备**。默认每日北京时间 10:00 执行一次检索和推送尝试。

项目使用的推送服务基于 [MeoW](https://www.chuckfang.com/MeoW/api_doc.html) 软件，目前仅支持搭载 HarmonyOS 5.0 及以上版本的设备。如需要，可自行将推送服务更改为适配其他操作系统的软件（例如 [Bark](https://apps.apple.com/cn/app/bark-%E7%BB%99%E4%BD%A0%E7%9A%84%E6%89%8B%E6%9C%BA%E5%8F%91%E6%8E%A8%E9%80%81/id1403753865) for iOS）并提交 fork 。

项目推荐用途为低频监控与个人提醒，例如课程通知、失物招领、库存/预约信息等主题。需要注意，**本项目并非爬虫，使用时请遵循[北大树洞服务协议](https://treehole.pku.edu.cn/ch/web/pc/serviceAgreement)，请勿使用本项目高频大量爬取北大树洞，尤其请勿将树洞内容外传，相关风险及后果请自负。同时，不建议在北大树洞内发表含有本项目或类似项目的树洞，以免遭到禁言。** 

北大树洞登录与搜索请求实现方式参考了 [SunVapor/pku-treehole-search-agent](https://github.com/SunVapor/pku-treehole-search-agent)。

## 功能

- 复用 PKU IAAA 登录态访问北大树洞。
- 按关键词搜索树洞帖子。
- 用状态文件记录已见过的 `pid`，只推送新增帖子。
- 推送正文按帖子列出正文和若干条评论预览。
- 支持本地运行，也支持部署到 PKU CLab 云主机并用 systemd timer 每天定时执行。
- 在 CLab 上可先登录北大网关，再执行树洞搜索和 MeoW 推送。
- 可选开启云端启动提醒，用于部署调试时确认 timer 确实触发。
- 云端定时任务失败时会尽量发送 MeoW 提醒，覆盖网关登录失败、缺少 `config_private.py`、找不到可用 Python、树洞搜索脚本异常退出等情况。

## 本地安装

```bash
git clone https://github.com/YaoXingjin/pku-treehole-keyword-autosearch.git
cd pku-treehole-keyword-autosearch
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Windows PowerShell 可直接使用：

```powershell
git clone https://github.com/YaoXingjin/pku-treehole-keyword-autosearch.git
cd pku-treehole-keyword-autosearch
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 配置

复制示例配置：

```bash
cp config_example.py config_private.py
```

Windows PowerShell：

```powershell
copy config_example.py config_private.py
```

编辑 `config_private.py`，至少填写：

- `USERNAME`: PKU IAAA 学号或账号
- `PASSWORD`: PKU IAAA 密码
- `KEYWORD`: 要检索的关键词
- `MEOW_NICKNAME`: MeoW 昵称

也可以完全用环境变量覆盖：

```bash
export TREEHOLE_USERNAME="<your_pku_id>"
export TREEHOLE_PASSWORD="<your_password>"
export TREEHOLE_KEYWORD="<keyword>"
export MEOW_NICKNAME="<your_meow_nickname>"
```

常用可选项：

- `TREEHOLE_COMMENT_LIMIT`: 每条帖子从树洞接口抓取的评论数，默认 `10`
- `TREEHOLE_STATE_FILE`: 状态文件路径，默认 `seen_posts_state.json`
- `MEOW_COMMENT_LIMIT`: 每条帖子在推送正文中展示的评论数，默认 `5`
- `MEOW_MAX_CHARS`: 推送正文最大字符数，默认 `1800`
- `MEOW_ENABLED`: 设为 `0`、`false`、`no` 或 `off` 时只打印不推送
- `MEOW_BASE_URL`: MeoW API 地址，默认 `https://api.chuckfang.com`
- `MEOW_DIRECT_FALLBACK`: MeoW 推送失败时绕过代理直连重试，默认开启
- `MEOW_STARTUP_NOTIFY`: 设为 `1`、`true`、`yes` 或 `on` 时，云端脚本启动时发送 MeoW 提醒；默认关闭，避免每天定时运行都推送启动消息

`config_private.py`、cookie、日志和状态文件都已在 `.gitignore` 中排除，请不要提交。

## 本地手动测试

在项目目录下执行，验证 MeoW 推送链路：

```bash
python search_keyword.py --test-push
```

执行真实搜索：

```bash
python search_keyword.py
```

脚本会：

1. 登录或复用北大树洞登录态。
2. 按关键词搜索帖子。
3. 和状态文件里的历史 `pid` 比较。
4. 有新增帖子时发送一条 MeoW 推送。
5. 更新状态文件。

首次登录可能需要按提示输入短信验证码或手机令牌。

### 推送格式

标题：

```text
检索到 n 条「关键词」树洞
```

正文示例：

```text
1. #8285993 | 2026-06-06 10:41:40 | 评论 2
   > 帖子正文预览
   -  评论预览 1
   -  评论预览 2
```

## 云端部署

PKU CLab 云主机创建和连接方式可参考官方文档：[CLab 快速上手](https://clab.pku.edu.cn/docs/getting-started/introduction)。

部署到云主机的完整步骤见 [DEPLOY.md](DEPLOY.md)。

典型流程：

1. 在 CLab 创建共享网络 `pku` 或 `pku-new` 上的云主机。本项目只在 `rocky` 主机上进行了验证。
2. 将本仓库同步到云主机任意目录；推荐 `~/pku-treehole-keyword-autosearch`。
3. 手动上传 `config_private.py`，并设置 `chmod 600 config_private.py`。
4. 安装依赖。
5. 写入 `PROJECT_DIR` 环境文件并启用 `deploy/treehole-search.timer`。

CLab 云主机访问互联网前通常需要登录北大网关。本项目提供 `scripts/its_network_login.py`，可复用树洞账号密码完成网关登录。

建议在云端 systemd 环境文件中同时写入 `MEOW_NICKNAME`。这样即使 `config_private.py` 缺失或 Python 环境不完整，失败提醒也更有机会发到手机。部署调试时如需确认 timer 是否触发，可临时设置 `MEOW_STARTUP_NOTIFY=1` 开启启动提醒。

云主机运行状态可通过 systemd 和日志检查：

```bash
systemctl --user status treehole-search.timer
systemctl --user list-timers --all | grep treehole
systemctl --user status treehole-search.service
tail -n 100 logs/treehole-search.log
```

更完整的检查步骤见 [DEPLOY.md](DEPLOY.md#7-检查运行状态)。

## 文件结构

```text
client.py                         树洞登录和搜索 API 封装
meow_push.py                      MeoW 推送封装
search_keyword.py                 主入口脚本
config_example.py                 配置模板
DEPLOY.md                         CLab 云端部署说明
deploy/treehole-search.service    systemd user service 模板
deploy/treehole-search.timer      systemd user timer 模板
scripts/check_deploy_ready.sh     云端部署检查
scripts/its_network_login.py      CLab 网关登录
scripts/run_treehole_search.sh    云端定时运行入口
```

## 隐私和安全

- 不要提交 `config_private.py`。
- 不要提交 cookie、状态文件、日志文件。
- 云端部署时建议执行 `chmod 600 config_private.py`。
- 如果公开 fork 或发布仓库，先运行一次脱敏扫描，确认没有个人昵称、学号、密码、IP、SSH 路径或真实树洞内容。

## License

MIT License. See [LICENSE](LICENSE).
