# 性能与内存建议

OpenDeepSeek 不应该为了启动项目把电脑拖慢。默认策略是核心服务优先，搜索和重任务按需开启。

## 推荐模式

### 轻量模式

```bash
./setup.sh start
```

只启动 Open WebUI、Smart Bridge、Hermes。适合日常聊天、文件任务、网页生成和本机 Agent 演示。

### 完整模式

```bash
./setup.sh start-full
```

额外启动 SearXNG。适合实时搜索、新闻早报、资料调研。低内存电脑不建议默认开启。

### 停止释放内存

```bash
./setup.sh stop
```

这只停止容器，不删除聊天记录和 Docker volume。

## 默认资源上限

```env
HERMES_CPUS=1.5
HERMES_MEMORY_LIMIT=1280m
WEBUI_CPUS=1.0
WEBUI_MEMORY_LIMIT=1024m
BRIDGE_CPUS=0.5
BRIDGE_MEMORY_LIMIT=256m
SEARXNG_CPUS=0.5
SEARXNG_MEMORY_LIMIT=384m
```

不要降低：

```env
HERMES_AGENT_MAX_TOKENS=32768
```

这个不是内存开关，而是长任务输出预算。做网页、PPT、报告时降低它容易被截断。

## 速度优化

默认关闭 Open WebUI 的额外模型调用：

```env
ENABLE_TITLE_GENERATION=false
ENABLE_TAGS_GENERATION=false
ENABLE_FOLLOW_UP_GENERATION=false
ENABLE_CODE_INTERPRETER=false
ENABLE_RAG_HYBRID_SEARCH=false
```

这些功能会给每次对话增加额外请求。Creator Release 优先保证主回复速度。

## 什么时候会慢

- 第一次拉镜像或启动 Open WebUI。
- 第一次使用 RAG/embedding。
- 启用 `--profile full` 后 SearXNG 占用额外内存。
- 真 Agent 任务需要读写文件、跑脚本或多轮工具执行。
- 自定义 Provider 的延迟/限速比 DeepSeek 更差。

## 快速释放内存

```bash
./setup.sh stop
```

不删除聊天记录和 volume。需要重新使用时再运行：

```bash
./setup.sh --web
```
