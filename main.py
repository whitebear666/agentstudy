from __future__ import annotations

import argparse
from typing import List, Optional

from models import UserPrefs
from agent import GroceryMealAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grocery/Meal Planning Agent (MVP). Generates meal_plan.md and shopping_list.json."
    )
    parser.add_argument("--people", type=int, default=2, help="Number of people (default: 2)")
    parser.add_argument("--days", type=int, default=3, help="Number of days to plan (default: 3)")
    parser.add_argument("--budget", type=float, default=None, help="Budget (optional)")
    parser.add_argument(
        "--avoid",
        nargs="*",
        default=[],
        help="Avoid ingredients (e.g. --avoid 香菜 辣椒). Default: none",
    )
    parser.add_argument("--cuisine", type=str, default="家常", help="Cuisine style (default: 家常)")
    parser.add_argument(
        "--no-kitchen",
        action="store_true",
        help="If set, indicates you do NOT have a kitchen (default: have kitchen).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    prefs = UserPrefs(
        people=args.people,
        days=args.days,
        budget=args.budget,
        avoid=args.avoid if args.avoid else None,
        cuisine=args.cuisine,
        has_kitchen=not args.no_kitchen,
    )

    agent = GroceryMealAgent()
    agent.run(prefs)
    print("Done. See output/meal_plan.md and output/shopping_list.json")


if __name__ == "__main__":
    main()