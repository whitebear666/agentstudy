# main.py
from models import UserPrefs
from agent import GroceryMealAgent

def main():
    # 你后面可以改成交互式输入；先写死参数保证能跑通
    prefs = UserPrefs(
        people=2,
        days=3,
        budget=150,
        avoid=["香菜"],  # 示例
        cuisine="家常",
        has_kitchen=True,
    )
    agent = GroceryMealAgent()
    agent.run(prefs)
    print("Done. See output/meal_plan.md and output/shopping_list.json")

if __name__ == "__main__":
    main()