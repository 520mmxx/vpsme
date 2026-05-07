# OpenDeepSeek 中文文档

OpenDeepSeek CN 的目标是：中文优先、国内网络友好、一键安装、真 Agent、能看到产物。

## 普通用户

- [我应该下载哪个版本](00-我应该下载哪个版本.md)
- [国内网络问题](04-国内网络问题.md)
- [离线安装](05-离线安装.md)
- [填写 DeepSeek Key](06-填写DeepSeek-Key.md)
- [文件权限说明](07-文件权限说明.md)

## 维护者

- [离线包发布流程](离线包发布流程.md)
- [发布检查清单](../RELEASE-CHECKLIST.md)
- [OpenDeepSeek CN 路线图](../OPENDEEPSEEK-CN-ROADMAP.md)

## 当前状态

本地产品化链路已完成：

- 中国版安装脚本和 compose 骨架
- 国内网络体检
- 国内镜像与离线包构建脚本
- 中文 onboarding / Portal
- Artifact Manifest 和本机只读预览服务
- `opendeepseek-auto` / `fast` / `agent` / `deepwork` 四个产品模式

真正对外宣称 China Ready 前，还需要维护者完成：

- 保持 Gitee raw 安装脚本同步，并补齐 GitCode 仓库镜像
- 推送国内容器镜像
- 上传离线包到 OSS/COS
- 填写 `release-cn.json` 的真实 URL、checksum、image digest
- 启动 Docker stack 后运行完整 smoke-test
