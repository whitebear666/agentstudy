# agentstudy：买菜 / 食谱规划 Agent（从 0 手搓）

这是一个从 0 开始实现的“买菜/食谱规划 Agent”最小可用版本（MVP）。

它会根据人数、天数、忌口等偏好生成：

- **N 天食谱规划**（Markdown）
- **购物清单**（JSON）

并把结果写入本地文件，便于你在日常生活中快速做饭规划与买菜准备。

## 功能特性

- 离线可运行（当前版本不依赖外部大模型/网络）
- 工具化设计（读取冰箱清单 JSON、写出 Markdown/JSON）
- 输出可验收（固定产物文件）

## 项目结构

```
agentstudy/
  main.py              # 程序入口
  agent.py             # Agent：规划食谱 + 生成购物清单 + 落盘
  models.py            # 数据结构
  tools.py             # 工具：读写 JSON/文本
  data/
    fridge.json         # 冰箱/现有食材示例
  output/               # 运行后生成（已在 .gitignore 中忽略）
```

## 快速开始

### 1) 环境要求

- Python 3.10+（推荐 3.11）

### 2) 运行

在项目根目录执行：

```bash
python main.py
```

运行成功后，会生成：

- `output/meal_plan.md`
- `output/shopping_list.json`

### 3) 修改你的冰箱清单（可选）

编辑：`data/fridge.json`

把你家里已有的食材写进去，Agent 生成购物清单时会尽量避免重复购买。

## 如何自定义

- 修改 `main.py` 里的参数：人数 `people`、天数 `days`、预算 `budget`、忌口 `avoid` 等。
- 在 `agent.py` 的 `RECIPE_DB` 增加/调整菜谱库。

## 下一步计划（升级为真正 AI Agent）

- 支持命令行/交互式输入
- 引入大模型（Qwen / OpenAI）做更智能的选菜与步骤生成
- 对输出增加 JSON Schema 校验与重试（更稳）