# agentstudy：买菜 / 食谱规划 Agent（从 0 手搓）

这是一个从 0 开始实现的“买菜/食谱规划 Agent”最小可用版本（MVP）。

它会根据人数、天数、预算、忌口、口味等偏好生成：

- **N 天食谱规划**（`output/meal_plan.md`）
- **购物清单**（`output/shopping_list.json`）
- **本次生成所用参数**（`output/prefs.json`，便于复现/答辩）

---

## 功能特性

- 支持**对话式多轮输入**（可逐步补充/修改）
- 支持 **撤销（undo）/重置（reset）/查看当前偏好**
- 生成结果写入本地文件，适合日常做饭规划与买菜准备
- 核心生成逻辑可离线运行（不依赖大模型）
- 引入 Qwen（可选）用于更自然的参数抽取

---

## 项目结构

```
agentstudy/
  main.py              # 离线入口（不依赖大模型）
  agent.py             # 生成：食谱规划 + 购物清单 + 落盘
  models.py            # 数据结构
  tools.py             # 工具：读写 JSON/文本

  chat_ui_qwen.py      # Tkinter 对话 UI（推荐）
  agent_controller.py  # 对话控制器（多轮状态、追问、生成）
  conversation.py      # 会话状态（prefs + confirmed_fields）
  intent.py            # 意图识别（生成/重置/撤销等）
  prefs_extractor.py   # 偏好抽取（本地规则兜底 + Qwen）

  llm_qwen.py          # Qwen 客户端
  prompts.py           # 提示词

  data/
    fridge.json        # 冰箱/现有食材示例
  output/              # 运行后生成（已在 .gitignore 中忽略）
  tests/               # 离线测试（pytest）
```

---

## 快速开始

### 1) 环境要求
- Python 3.10+（推荐 3.11）

### 2) 安装依赖（仅测试需要）
如果你要跑测试：

```bash
pip install -r requirements.txt
```

---

## 运行方式 A：对话 UI（使用Qwen-Turbo 因为便宜🤣）

### 1) 配置 API Key
参考 `.env.example`，将你的 key 配置到环境变量（推荐）：

- Windows PowerShell：
  ```powershell
  setx QWEN_API_KEY "你的key"
  ```

或在当前终端临时设置：

```powershell
$env:QWEN_API_KEY="你的key"
```

> 注意：不要把真实 key 提交到仓库。

### 2) 启动 UI
在项目根目录：

```bash
python chat_ui_qwen.py
```

### 3) 对话指令
- `生成 / 开始`：生成输出文件
- `当前偏好 / 参数`：查看当前记住的参数
- `撤销 / undo`：撤销上一条更新
- `重置 / reset`：清空会话
- `帮助`：查看示例

---

## 运行方式 B：离线运行（不依赖大模型）

```bash
python main.py
```

运行成功后会生成：
- `output/meal_plan.md`
- `output/shopping_list.json`

---

## 测试

```bash
pytest -q
```

---

## 下一步计划
- 更丰富的菜谱库、支持替换某天某餐
- 购物清单按分类导出（蔬菜/肉类/调料/主食）
- 加入预算约束与营养/热量目标