# 美食智能体 (Food Agent)

推理驱动的本地美食智能体:基于本地 Ollama `qwen3.5:0.8b` 模型,采用 ReAct 循环(Thought → Action → Observation → Final Answer),通过本地工具查询真实菜谱/营养数据后再回答,防止小模型凭空编造。

## 功能

- **菜谱查询** `search_recipe`:食材、步骤、难度、耗时
- **营养查询** `nutrition`:每 100 克热量与宏量营养
- **口味推荐** `recommend`:按菜系/口味推荐菜品
- **推理可视化**:Web 页面可展开查看每一步模型决策与工具调用
- 两种使用方式:命令行交互 / 粉色玻璃拟态 Web 聊天页面

## 环境要求

- Python 3.8+(仅用标准库,无需 pip 安装)
- [Ollama](https://ollama.com) 并已拉取模型:`ollama pull qwen3.5:0.8b`

## 使用

```bash
# 方式一: 命令行交互
python food_agent.py
# 或单次提问
python food_agent.py "宫保鸡丁怎么做"

# 方式二: Web 页面
python server.py
# 浏览器打开 http://localhost:8000
```

## 文件说明

| 文件 | 说明 |
|---|---|
| `food_agent.py` | 智能体核心:ReAct 推理循环 + 本地工具 + Ollama 调用 |
| `server.py` | Web 后端:标准库 HTTP 服务,提供 `/api/chat`、`/api/health` |
| `index.html` | Web 前端:粉色玻璃拟态聊天页面,支持推理过程展开 |

## 架构

```
用户问题
  → qwen3.5:0.8b 输出 Action: 工具名(参数)
  → 本地工具执行, 返回真实 Observation
  → 回填 Observation, 模型继续推理或输出 Final Answer
  → 回答必须忠于工具数据 (防编造机制)
```
