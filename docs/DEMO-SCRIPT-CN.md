# OpenDeepSeek CN 演示脚本

这份脚本用于发布视频、README 动图或路演演示。目标不是讲架构，而是让普通用户看到：它真的能装、能聊、能干活、能找到产物。

## 0. 演示前准备

```bash
./setup.sh verify
python3 scripts/benchmark_routing.py
scripts/release-gate.sh
```

如果要做真实端到端演示：

```bash
docker compose up -d
scripts/release-gate.sh --full
```

## 1. 开场

画面：打开 `http://localhost:3001`。

讲法：

```text
这不是又一个 DeepSeek 聊天壳子。
普通问题它走便宜快速的 V4 Flash；
真正要读文件、写网页、做报告、设置提醒，它会切到 Hermes Agent 真执行。
```

## 2. 四种模式

画面：展示 Portal 的四个模式卡片。

要点：

- 自动模式：默认推荐
- 极速问答：便宜快
- 真 Agent：操作电脑和文件
- 深度任务：长报告、复杂代码、多步骤任务

## 3. 填 Key

画面：引导页填写 DeepSeek API Key。

讲法：

```text
Key 只写进本机 .env，不上传，不提交。
小白不需要理解 Docker、Bridge、Hermes 这些底层词。
```

## 4. 普通问答

提示词：

```text
用一句话解释 OpenDeepSeek 是什么。
```

预期：

- 秒回
- 不进 Hermes
- 不调用文件工具

## 5. 真 Agent 生成网页

提示词：

```text
请在 /host/OpenDeepSeek-Outputs/demo-site 里生成一个单文件中文介绍页 index.html，介绍 OpenDeepSeek：普通问答快，真任务走 Hermes Agent，产物可预览。完成后验证文件存在。
```

预期：

- 先出现“切到 Agent，请稍等”
- Hermes 实际写文件
- 回复包含 `/host/...` 和本机路径
- 回复追加 OpenDeepSeek 产物卡片
- `http://localhost:8770/artifacts/.../index.html` 可预览

## 6. 文件权限

画面：Portal 文件权限说明。

讲法：

```text
默认先只给 OpenDeepSeek 专用目录，想让它看桌面再授权。
这比一上来全盘读写更适合普通用户。
```

## 7. 国内安装线

画面：README 中国版安装命令。

讲法：

```text
国内用户不能被 GitHub raw、GHCR、Docker Hub 卡死。
所以 OpenDeepSeek CN 单独准备了 Gitee、GitCode、国内镜像和离线包。
```

## 8. 收尾

讲法：

```text
OpenDeepSeek 的价值不是把 DeepSeek 包成聊天框。
它是让便宜的 DeepSeek API 进入真实 Agent 工作流：
用户多用，模型多在 Agent 场景里试错，下一代模型才会更会干活。
```
