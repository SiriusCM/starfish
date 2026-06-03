---
name: bt2docker
summary: 把宝塔环境的游戏后端架设教程转换为可一键执行的 Docker Compose 部署方案
triggers: 宝塔,baota,bt,docker,部署,架设,游戏后端,Linux 架设,宝塔教程,centos,nginx,mysql,php,mongo,mongodb
domains: ["*"]
enabled: true
---

# Skill: 宝塔教程 → Docker Compose 部署转换

当用户提供一份"基于宝塔面板"的游戏服务端架设教程，请按本剧本输出一份**等价的 Docker 部署方案**，并通过 MCP 的 `shell.run` 工具执行命令完成部署。

---

## 转换原则（最重要）

| 宝塔做什么 | Docker 等价做法 |
|---|---|
| 安装 Nginx / PHP / MySQL / MongoDB | 用 `docker-compose.yml` 拉对应镜像（版本对齐教程） |
| PHP 安装额外扩展（如 `mongo`/`mongodb`/`redis`/`swoole`） | 用 `php:5.6-fpm` / `php:7.x-fpm` 等镜像 + `Dockerfile` 装扩展，构建自定义镜像 |
| 网站目录 `/www/wwwroot/<site>` | 用 volume 挂载到 `nginx` 容器的 `/var/www/html`（或教程指定路径） |
| 服务端目录 `/server` 与 `usr/local/mongodb` 等 | 同样 volume 挂到对应容器 |
| 防火墙放行端口 | 在 `docker-compose.yml` 的 `ports` 段直接暴露 |
| 修改 `etc/profile` 加环境变量 | 写入容器的 `environment:` 或 `entrypoint.sh` |
| 启动脚本（`nohup ./logic ${SERVER}` 等） | 写一个 `logic` 服务容器（用 ubuntu/debian/alpine 跑二进制），或用 `command:` 直接拉起 |
| 数据库初始密码 / GM 码 | 通过 environment 变量注入（保留教程里的原值） |

---

## 镜像来源

**国内拉镜像走加速地址 `docker.xuanyuan.run`**。在 `docker pull` 命令前加前缀：

```bash
# 示例：拉 mysql:5.6
docker pull docker.xuanyuan.run/library/mysql:5.6
docker tag docker.xuanyuan.run/library/mysql:5.6 mysql:5.6
```

或直接在 `docker-compose.yml` 的 `image:` 字段写完整地址：

```yaml
image: docker.xuanyuan.run/library/mysql:5.6
```

非官方镜像（用户/组织名）：`docker.xuanyuan.run/<user>/<repo>:<tag>`。

---

## 输出格式（必须严格按这五段输出）

### 1) 部署目录结构
列出建议的目录树，例如：
```
~/game-deploy/
├── docker-compose.yml
├── php/Dockerfile          # 若需自定义 PHP 镜像
├── nginx/conf.d/site.conf
├── data/mysql/             # MySQL 数据持久化
├── data/mongo/             # MongoDB 数据持久化
└── volumes/
    ├── server/             # 教程里的 /server
    └── wwwroot/            # 教程里的 /www/wwwroot
```

### 2) 完整 `docker-compose.yml`
- 服务命名清晰（`nginx`、`php`、`mysql`、`mongo`、`logic-middle`、`logic-game` 等）
- 全部 `image:` 用 `docker.xuanyuan.run/...` 前缀
- 端口映射对齐教程
- 数据库密码、GM 码、目录路径**保留教程原值**
- 用 `depends_on` 表达启动顺序

### 3) 自定义 Dockerfile（如有）
比如 PHP 装 mongo 扩展：
```dockerfile
FROM docker.xuanyuan.run/library/php:5.6-fpm
RUN pecl install mongo && docker-php-ext-enable mongo
```

### 4) 一键部署 Shell 脚本
**通过 MCP 的 `shell.run` 工具执行。** 指出每条命令的作用：
1. 创建目录与上传压缩包
2. 解压（如教程里提到的 `unzip ckwy.zip`）
3. 替换 IP、配置文件中的占位符
4. `docker compose pull` / `build`
5. `docker compose up -d`
6. 进入特定容器执行教程里的"启动游戏服务"命令（用 `docker exec`）

**注意：所有命令必须通过 `shell.run` 工具执行，不要让用户复制到自己的终端**。除非用户明确说"我自己跑"。

### 5) 验证与故障处置
- `docker compose ps` 查容器状态
- `docker logs <container>` 查启动日志
- `docker exec -it <container> <cmd>` 复刻教程里的"聊天框输入 xxx"等运维操作
- 教程里提到的"首次卡读条 → reboot"映射为 `docker compose restart`
- 教程里提到的"芒果库需手动启动"映射为容器 `restart: unless-stopped` 或 healthcheck

---

## 必须保留教程里的关键信息

在输出前，请先从教程里**精确提取**以下要素并在结果开头列出：

| 字段 | 示例（仅示意） |
|---|---|
| 服务端目录 | `/server` |
| 网站目录 | `/www/wwwroot/<name>` |
| 数据库密码 | （教程里的原值，照搬） |
| GM 码 / 后台密码 | （照搬） |
| 玩家后台 / CDK 后台 URL | （照搬） |
| 客户端要修改的文件 | `assets/.../index.*.js` |
| 启动入口（二进制 / 脚本） | `./logic middle` / `./logic ${SERVER}` 等 |
| 默认 IP 占位 | 教程里写的那个 IP，替换成 `{{HOST_IP}}` 让用户填 |

---

## 行为规则

1. 一上来先**回答一句**："识别到一份基于宝塔的架设教程，转换为 Docker Compose 部署方案如下："
2. 五段内容**全部用代码块**输出，便于复制
3. 所有 `image:` 字段都用 `docker.xuanyuan.run/...`
4. 涉及"通过命令行做"的步骤，**必须通过 `shell.run` 工具执行**，每步执行后等待用户确认再继续；不要 `&&` 串很多命令一口气跑（出错难定位）
5. 默认部署目录 `~/game-deploy/`，除非用户指定其他位置
6. 端口冲突时优先建议宿主机端口加偏移（如 `3306 → 3307`），保留容器内端口不变
7. 教程里**写死的 IP** 全部替换为 `{{HOST_IP}}`，并在最后提示用户用 `sed -i` 替换
8. 教程里**目录的 777 权限**改成挂载 volume 的方式（容器内本就有完整权限），不要在宿主上 `chmod 777`
9. 涉及"重启 PHP / 重启服务"的步骤，转换为 `docker compose restart <svc>`
10. 不要使用宝塔面板地址、用户名、密码等敏感信息，除非用户明确要求保留

---

## 失败时降级

如果某个组件没有合适的现成镜像（例如教程里某个二进制依赖很奇怪的旧 glibc），就：

1. 给一个 `Dockerfile`，FROM 教程对应的系统版本（`docker.xuanyuan.run/library/centos:7`）
2. 在 Dockerfile 里照搬教程的 yum/wget 命令
3. 二进制和脚本通过 volume 挂入容器内执行
4. 明确告诉用户："因 X 原因，<服务名> 改用基于 centos:7 的自定义镜像而非官方镜像"