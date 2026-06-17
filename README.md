# 今天吃点撒：买菜 / 食谱规划 Agent（从 0 手搓）

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
├── 应用入口层
│ ├── chat_ui_qwen.py # Tkinter 对话 UI（推荐）
│ └── main.py # 离线入口（不依赖大模型）
│
├── Agent 核心层
│ ├── agent.py # 生成：食谱规划 + 购物清单 + 落盘
│ ├── agent_controller.py # 对话控制器（多轮状态、追问、生成）
│ ├── conversation.py # 会话状态（prefs + confirmed_fields）
│ ├── models.py # 数据结构（UserPrefs/Meal/MealSet/DayPlan）
│ └── tools.py # 工具：读写 JSON/文本
│
├── 对话理解层
│ ├── intent.py # 意图识别（生成/重置/撤销等）
│ ├── prefs_extractor.py # 偏好抽取（本地规则兜底 + Qwen）
│ └── prompts.py # 提示词模板
│
├── LLM 服务层
│ └── llm_qwen.py # Qwen 客户端封装
│
├── Skill 能力层
│ ├── meal_composer.py # 菜单组合生成
│ ├── meal_classifier.py # 菜品分类
│ ├── meal_replace.py # 动态替换
│ ├── pantry_aware.py # 冰箱食材感知
│ ├── nutrition_calculator.py # 营养评估
│ ├── budget_enforcer.py # 预算硬约束
│ └── shopping_list_optimizer.py # 购物清单优化
│
├── 数据处理脚本
│ ├── tag_recipes.py # 菜谱标签生成
│ └── import_howtocook.py # 导入菜谱数据
│
├── 数据层
│ ├── data/
│ │ ├── recipes_tagged.json # 标签化菜谱库（390+ 菜品）
│ │ ├── fridge.json # 冰箱库存示例
│ │ └── kitchen.json # 厨具配置
│ └── output/ # 运行后生成（.gitignore 忽略）
│ ├── meal_plan.md
│ ├── shopping_list.json
│ ├── shopping_list.md
│ ├── shopping_list_optimized.json
│ ├── nutrition_report.md
│ └── prefs.json
│
├── 硬件接口层
│ └── hardware/
│ └── hardware_interface.py # ESP8266/NFC 预留接口
│
├── 测试层
│ └── tests/ # 离线测试（pytest）
│
├── 配置文件
│ ├── .env.example # 环境变量示例
│ ├── requirements.txt # Python 依赖
│ └── README.md # 项目说明
│
└── 旧脚本
└── chat_ui.py # 备用聊天界面（已废弃）             # 离线测试（pytest）
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
- 硬件加入，系统将支持手机视觉方案或NFC
- 接入HA平台
- 将价格源扩展
