/*
 * Role:
 *   React/Vite web client for the meal-planning agent.
 *
 * Related modules:
 *   api_server.py provides menu, recipe, pantry, and chat APIs.
 *   frontend/src/styles.css owns the Apple-like visual system for these views.
 */
import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BookOpen,
  Ban,
  ChefHat,
  Clock3,
  Eye,
  Heart,
  Leaf,
  ListChecks,
  MessageCircle,
  Pin,
  RefreshCw,
  Send,
  ShoppingBag,
  Sparkles,
  Star,
  Trash2,
  Utensils,
  PackagePlus,
  Download,
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const T = {
  appTitle: "\u4eca\u5929\u5403\u70b9\u5565",
  plan: "\u89c4\u5212",
  mini: "\u5c0f\u7a0b\u5e8f",
  recipes: "\u83dc\u54c1",
  assistant: "\u52a9\u624b",
  pantry: "\u5e93\u5b58",
  formTitle: "\u586b\u5199\u89c4\u5212\u4fe1\u606f",
  generate: "\u751f\u6210\u83dc\u5355",
  generating: "\u751f\u6210\u4e2d",
  people: "\u4eba\u6570",
  days: "\u89c4\u5212\u5929\u6570",
  budget: "\u9884\u7b97",
  cuisine: "\u53e3\u5473/\u83dc\u7cfb",
  dishCount: "\u6bcf\u9910\u51e0\u9053\u83dc",
  meatCount: "\u51e0\u8364",
  vegCount: "\u51e0\u7d20",
  healthGoal: "\u5065\u5eb7\u76ee\u6807",
  avoid: "\u5fcc\u53e3/\u8fc7\u654f",
  breakfastStyle: "\u65e9\u9910\u504f\u597d",
  lunchStyle: "\u5348\u9910\u504f\u597d",
  dinnerStyle: "\u665a\u9910\u504f\u597d",
  home: "\u5bb6\u5e38",
  light: "\u6e05\u6de1",
  sichuan: "\u5ddd\u83dc",
  fatLoss: "\u51cf\u8102",
  cantonese: "\u7ca4\u83dc",
  none: "\u4e0d\u6307\u5b9a",
  muscle: "\u589e\u808c",
  maintain: "\u7ef4\u6301",
  gain: "\u589e\u91cd",
  mealPlan: "\u83dc\u5355\u89c4\u5212",
  noMenu: "\u8fd8\u6ca1\u6709\u751f\u6210\u83dc\u5355",
  noMenuHint: "\u5728\u4e0a\u65b9\u8868\u5355\u586b\u5199\u4eba\u6570\u3001\u9884\u7b97\u3001\u8364\u7d20\u548c\u53e3\u5473\u540e\u751f\u6210\u3002",
  view: "\u67e5\u770b",
  replace: "\u6362\u4e00\u9053",
  replaceLight: "\u6e05\u6de1",
  replaceFast: "\u5feb\u624b",
  replaceVeg: "\u7d20\u83dc",
  replaceProtein: "\u9ad8\u86cb\u767d",
  rerollMeal: "\u91cd\u6392\u8fd9\u9910",
  rerollDay: "\u91cd\u6392\u8fd9\u5929",
  remove: "\u5220\u9664",
  fixed: "\u5df2\u56fa\u5b9a",
  fix: "\u56fa\u5b9a",
  recipeLibrary: "\u83dc\u54c1\u5e93",
  searchRecipe: "\u641c\u7d22\u83dc\u540d",
  selectedOnly: "\u53ea\u770b\u5df2\u9009",
  clearSelected: "\u6e05\u7a7a\u9009\u62e9",
  addToList: "\u52a0\u5165\u6e05\u5355",
  selected: "\u5df2\u9009\u62e9",
  favorite: "\u6536\u85cf",
  favorited: "\u5df2\u6536\u85cf",
  favoriteMenu: "\u6536\u85cf\u8fd9\u4efd\u83dc\u5355",
  favoriteMenus: "\u6536\u85cf\u83dc\u5355",
  blacklist: "\u4e0d\u559c\u6b22",
  blacklisted: "\u5df2\u5c4f\u853d",
  hideBlacklisted: "\u9690\u85cf\u9ed1\u540d\u5355",
  blacklistCount: "\u9ed1\u540d\u5355",
  favoriteCount: "\u6536\u85cf",
  selectedShopping: "\u591a\u83dc\u8d2d\u4e70\u6e05\u5355",
  selectedHint: "\u52fe\u9009\u83dc\u54c1\u540e\u8fd9\u91cc\u4f1a\u6c47\u603b\u98df\u6750\u3002",
  ingredients: "\u98df\u6750",
  steps: "\u505a\u6cd5",
  noRecipes: "\u6682\u65e0\u83dc\u8c31\u6570\u636e",
  expiringOnly: "\u53ea\u770b\u4e34\u671f\u98df\u6750\u53ef\u505a",
  chatTitle: "\u5bf9\u8bdd\u52a9\u624b",
  thinking: "\u601d\u8003\u4e2d",
  online: "\u5728\u7ebf",
  you: "\u4f60",
  send: "\u53d1\u9001",
  allShopping: "\u5168\u83dc\u5355\u8d2d\u4e70\u6e05\u5355",
  shoppingEmpty: "\u751f\u6210\u83dc\u5355\u540e\u4f1a\u663e\u793a\u9700\u8981\u8d2d\u4e70\u7684\u98df\u6750\u3002",
  addPantry: "\u6dfb\u52a0\u5e93\u5b58",
  pantryName: "\u98df\u6750\u540d",
  quantity: "\u6570\u91cf",
  unit: "\u5355\u4f4d",
  category: "\u5206\u7c7b",
  pantryHint: "\u5e93\u5b58\u4e2d\u5df2\u6709\u7684\u98df\u6750\uff0c\u751f\u6210\u8d2d\u7269\u6e05\u5355\u65f6\u4f1a\u81ea\u52a8\u6263\u9664\u3002",
  templates: "\u573a\u666f\u6a21\u677f",
  timeline: "\u53a8\u623f\u65f6\u95f4\u8f74",
  reasons: "\u63a8\u8350\u7406\u7531",
  exportMenu: "\u5bfc\u51fa\u83dc\u5355",
  exportShopping: "\u5bfc\u51fa\u8d2d\u7269\u6e05\u5355",
  hideDone: "\u9690\u85cf\u5df2\u8d2d\u4e70",
  expiryDate: "\u4fdd\u8d28\u671f",
  expiringSoon: "\u4e34\u671f",
  expired: "\u5df2\u8fc7\u671f",
  expiringTitle: "\u4e34\u671f\u5e93\u5b58\u63d0\u9192",
  expiringHint: "\u8fd9\u4e9b\u98df\u6750\u4f1a\u5728\u751f\u6210\u83dc\u5355\u65f6\u81ea\u52a8\u4f18\u5148\u4f7f\u7528\u3002",
  useExpiring: "\u7528\u8fd9\u4e9b\u98df\u6750\u751f\u6210",
  daysLeft: "\u5269\u4f59",
  menuHistory: "\u83dc\u5355\u5386\u53f2",
  restoreHistory: "\u6062\u590d",
  viewDetail: "\u8be6\u60c5",
  noHistory: "\u751f\u6210\u83dc\u5355\u540e\u4f1a\u4fdd\u5b58\u6700\u8fd1\u5386\u53f2\u3002",
  noFavoriteMenus: "\u6536\u85cf\u559c\u6b22\u7684\u6574\u4efd\u83dc\u5355\u540e\u4f1a\u51fa\u73b0\u5728\u8fd9\u91cc\u3002",
  detail: "\u8be6\u60c5",
  close: "\u5173\u95ed",
  currentMenu: "\u5f53\u524d\u83dc\u5355",
  quickActions: "\u5feb\u6377\u64cd\u4f5c",
  dismiss: "\u5173\u95ed",
  preference: "Preferences",
  breakfast: "\u65e9\u9910",
  lunch: "\u5348\u9910",
  dinner: "\u665a\u9910",
  main: "\u4e3b\u83dc",
  side: "\u914d\u83dc",
  staple: "\u4e3b\u98df",
  soup: "\u6c64",
  minutes: "\u5206\u949f",
  difficulty: "\u96be\u5ea6",
  score: "\u8bc4\u5206",
};

const initialPrefs = {
  people: 2,
  days: 1,
  budget: 100,
  cuisine: T.home,
  avoid: "",
  dish_count: 3,
  meat_count: 1,
  vegetable_count: 2,
  breakfast_style: "",
  lunch_style: "",
  dinner_style: T.light,
  health_goal: "",
};

const quickPrompts = [
  "2\u4e2a\u4eba\u4e00\u8364\u4e24\u7d20\uff0c\u9884\u7b97150\uff0c\u751f\u6210",
  "\u6bcf\u99103\u9053\u83dc\uff0c\u665a\u9910\u6e05\u6de1\u4e00\u70b9",
  "\u4e0d\u8981\u592a\u8fa3\uff0c30\u5206\u949f\u5de6\u53f3",
  "\u5168\u7d20\uff0c\u89c4\u52122\u5929",
];

const scenarioTemplates = [
  { label: "\u5de5\u4f5c\u65e5\u665a\u9910", patch: { days: 1, budget: 80, dish_count: 2, meat_count: 1, vegetable_count: 1, dinner_style: "\u6e05\u6de1" } },
  { label: "30\u5206\u949f\u5feb\u624b\u9910", patch: { days: 1, budget: 80, dish_count: 2, meat_count: 1, vegetable_count: 1, dinner_style: "\u5feb\u624b" } },
  { label: "\u51cf\u8102\u4e00\u5468", patch: { days: 7, budget: 350, dish_count: 3, meat_count: 1, vegetable_count: 2, cuisine: "\u51cf\u8102", health_goal: "\u51cf\u8102" } },
  { label: "\u5e26\u996d\u83dc\u5355", patch: { days: 3, budget: 180, dish_count: 3, meat_count: 1, vegetable_count: 2, lunch_style: "\u9002\u5408\u5e26\u996d" } },
  { label: "\u670b\u53cb\u6765\u5bb6\u5403\u996d", patch: { people: 4, days: 1, budget: 240, dish_count: 5, meat_count: 2, vegetable_count: 3 } },
];

const mealTypes = [
  ["breakfast", T.breakfast],
  ["lunch", T.lunch],
  ["dinner", T.dinner],
];

const partTypes = [
  ["main", T.main],
  ["side", T.side],
  ["staple", T.staple],
  ["soup", T.soup],
];

function splitPlan(markdown) {
  if (!markdown) return [];
  return markdown
    .replace(/\r\n/g, "\n")
    .split(/\n(?=## Day|\n### )/g)
    .map((section) => section.trim())
    .filter(Boolean);
}

function shoppingItems(shoppingList) {
  return Object.entries(shoppingList?.items || shoppingList || {}).slice(0, 24);
}

function IconBadge({ icon: Icon, children }) {
  return (
    <span className="icon-badge">
      <Icon size={15} strokeWidth={2.2} />
      {children}
    </span>
  );
}

function Stat({ label, value, icon: Icon }) {
  return (
    <div className="stat">
      <Icon size={18} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function stars(value) {
  const score = Math.max(1, Math.min(5, value || 1));
  return "\u2605".repeat(score) + "\u2606".repeat(5 - score);
}

function downloadText(filename, text, type = "text/plain;charset=utf-8") {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function cleanRecipeSteps(steps = []) {
  return steps
    .map((step) => String(step || "").replace(/^\d+[\.、]\s*/, "").trim())
    .filter((step) => step && !step.includes("\u9884\u4f30") && !step.includes("![") && !/^https?:\/\//.test(step))
    .filter((step) => step.length <= 180)
    .slice(0, 12);
}

function expiryState(expiryDate) {
  if (!expiryDate) return "";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const expiry = new Date(`${expiryDate}T00:00:00`);
  if (Number.isNaN(expiry.getTime())) return "";
  const daysLeft = Math.ceil((expiry - today) / 86400000);
  if (daysLeft < 0) return "expired";
  if (daysLeft <= 3) return "soon";
  return "";
}

function useStoredList(key) {
  const [items, setItems] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(key) || "[]");
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(items));
  }, [key, items]);

  function toggle(item) {
    setItems((prev) => (prev.includes(item) ? prev.filter((name) => name !== item) : [...prev, item]));
  }

  return [items, toggle, setItems];
}

function useStoredJson(key, fallback) {
  const [value, setValue] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue];
}

function toggleStoredItem(items, setItems, item) {
  setItems((prev) => (prev.includes(item) ? prev.filter((name) => name !== item) : [...prev, item]));
}

function NoticeBar({ notice, onClose }) {
  if (!notice) return null;
  return (
    <div className={`notice-bar ${notice.type || "info"}`}>
      <span>{notice.message}</span>
      <button onClick={onClose}>{T.dismiss}</button>
    </div>
  );
}

function CompactDishList({ menu }) {
  if (!menu?.length) return <p className="muted">{T.noMenuHint}</p>;
  const firstDay = menu[0];
  return (
    <div className="compact-dish-list">
      {mealTypes.map(([mealType, mealLabel]) => {
        const meal = firstDay.meals?.[mealType];
        const names = Object.values(meal?.parts || {}).filter(Boolean).map((dish) => dish.name);
        if (!names.length) return null;
        return (
          <section key={mealType}>
            <span>{meal?.title || mealLabel}</span>
            <strong>{names.slice(0, 3).join(" / ")}</strong>
          </section>
        );
      })}
    </div>
  );
}

function MenuDetailModal({ item, onClose, onRestore }) {
  if (!item) return null;
  const artifacts = item.artifacts || {};
  const prefs = artifacts.prefs || {};
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section className="modal-panel" onClick={(event) => event.stopPropagation()}>
        <div className="panel-header tight">
          <div>
            <p className="eyebrow">{T.detail}</p>
            <h2><ChefHat size={21} /> {item.title}</h2>
          </div>
          <button className="select-action" onClick={onClose}>{T.close}</button>
        </div>
        <div className="stats-grid modal-stats">
          <Stat icon={ChefHat} label={T.people} value={prefs.people || "-"} />
          <Stat icon={ListChecks} label={T.days} value={prefs.days || "-"} />
          <Stat icon={ShoppingBag} label={T.budget} value={prefs.budget ? `¥${prefs.budget}` : "-"} />
          <Stat icon={Utensils} label={T.dishCount} value={prefs.dish_count ? `${prefs.dish_count}\u9053` : "-"} />
        </div>
        <CompactDishList menu={artifacts.menu} />
        <div className="modal-actions">
          <button className="primary-action" onClick={() => onRestore(item)}>
            <RefreshCw size={17} />
            {T.restoreHistory}
          </button>
          <button className="select-action" onClick={onClose}>{T.close}</button>
        </div>
      </section>
    </div>
  );
}

function ExpiringPantryAlert({ items, onGenerate, loading }) {
  if (!items?.length) return null;
  return (
    <section className="expiring-alert">
      <div>
        <p className="eyebrow">Pantry Alert</p>
        <h2><Clock3 size={21} /> {T.expiringTitle}</h2>
        <p>{T.expiringHint}</p>
      </div>
      <div className="expiring-items">
        {items.slice(0, 6).map((item) => (
          <span className={item.status === "expired" ? "expired" : ""} key={`${item.name}-${item.expiry_date}`}>
            {item.name}
            <em>{item.days_left < 0 ? T.expired : `${T.daysLeft} ${item.days_left} \u5929`}</em>
          </span>
        ))}
      </div>
      <button className="primary-action" disabled={loading} onClick={onGenerate}>
        <Sparkles size={17} />
        {loading ? T.generating : T.useExpiring}
      </button>
    </section>
  );
}

function PlanningForm({ form, setForm, onGenerate, loading, blacklistedCount, favoriteCount }) {
  function update(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <section className="panel form-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Meal Form</p>
          <h2><ListChecks size={21} /> {T.formTitle}</h2>
        </div>
        <button className="primary-action" disabled={loading} onClick={onGenerate}>
          <Sparkles size={17} />
          {loading ? T.generating : T.generate}
        </button>
      </div>
      {blacklistedCount ? (
        <p className="form-note">{T.blacklistCount}: {blacklistedCount} \u9053\u83dc\u5c06\u5728\u751f\u6210\u65f6\u81ea\u52a8\u6392\u9664</p>
      ) : null}
      {favoriteCount ? (
        <p className="form-note">{T.favoriteCount}: {favoriteCount} \u9053\u83dc\u4f1a\u5728\u751f\u6210\u65f6\u4f18\u5148\u63a8\u8350</p>
      ) : null}
      <div className="template-row">
        <span>{T.templates}</span>
        {scenarioTemplates.map((template) => (
          <button key={template.label} onClick={() => setForm((prev) => ({ ...prev, ...template.patch }))}>
            {template.label}
          </button>
        ))}
      </div>

      <div className="form-grid">
        <Field label={T.people}>
          <input type="number" min="1" max="10" value={form.people} onChange={(e) => update("people", e.target.value)} />
        </Field>
        <Field label={T.days}>
          <input type="number" min="1" max="14" value={form.days} onChange={(e) => update("days", e.target.value)} />
        </Field>
        <Field label={T.budget}>
          <input type="number" min="0" value={form.budget} onChange={(e) => update("budget", e.target.value)} />
        </Field>
        <Field label={T.cuisine}>
          <select value={form.cuisine} onChange={(e) => update("cuisine", e.target.value)}>
            {[T.home, T.light, T.sichuan, T.fatLoss, T.cantonese].map((item) => <option key={item}>{item}</option>)}
          </select>
        </Field>
        <Field label={T.dishCount}>
          <input type="number" min="1" max="6" value={form.dish_count} onChange={(e) => update("dish_count", e.target.value)} />
        </Field>
        <Field label={T.meatCount}>
          <input type="number" min="0" max="6" value={form.meat_count} onChange={(e) => update("meat_count", e.target.value)} />
        </Field>
        <Field label={T.vegCount}>
          <input type="number" min="0" max="6" value={form.vegetable_count} onChange={(e) => update("vegetable_count", e.target.value)} />
        </Field>
        <Field label={T.healthGoal}>
          <select value={form.health_goal} onChange={(e) => update("health_goal", e.target.value)}>
            <option value="">{T.none}</option>
            {[T.fatLoss, T.muscle, T.maintain, T.gain].map((item) => <option key={item}>{item}</option>)}
          </select>
        </Field>
        <Field label={T.avoid}>
          <input value={form.avoid} onChange={(e) => update("avoid", e.target.value)} placeholder="\u9999\u83dc\u3001\u8fa3\u6912\u3001\u725b\u5976" />
        </Field>
        <Field label={T.breakfastStyle}>
          <input value={form.breakfast_style} onChange={(e) => update("breakfast_style", e.target.value)} placeholder="\u7ca5\u3001\u9762\u3001\u6e05\u6de1" />
        </Field>
        <Field label={T.lunchStyle}>
          <input value={form.lunch_style} onChange={(e) => update("lunch_style", e.target.value)} placeholder="\u8981\u8089\u3001\u5c11\u6cb9" />
        </Field>
        <Field label={T.dinnerStyle}>
          <input value={form.dinner_style} onChange={(e) => update("dinner_style", e.target.value)} placeholder="\u6e05\u6de1\u3001\u5c11\u4e3b\u98df" />
        </Field>
      </div>
    </section>
  );
}

function dishKey(day, mealType, partType, name) {
  return `${day}:${mealType}:${partType}:${name}`;
}

function MenuEditor({ menu, onInspect, onReplace, onRemove, onRerollMeal, onRerollDay, fixedDishKeys, onToggleFixed }) {
  if (!menu?.length) return null;
  return (
    <div className="menu-editor">
      {menu.map((day) => (
        <article className="meal-card" key={day.day}>
          <div className="meal-card-header">
            <h3>Day {day.day}</h3>
            <button onClick={() => onRerollDay(day.day)}><RefreshCw size={15} /> {T.rerollDay}</button>
          </div>
          {mealTypes.map(([mealType, mealLabel]) => {
            const meal = day.meals?.[mealType];
            return (
              <section className="menu-meal-block" key={`${day.day}-${mealType}`}>
                <div className="meal-block-header">
                  <h4>{meal?.title || mealLabel}</h4>
                  <button onClick={() => onRerollMeal(day.day, mealType)}><RefreshCw size={15} /> {T.rerollMeal}</button>
                </div>
                <div className="menu-dish-grid">
                  {partTypes.map(([partType, partLabel]) => {
                    const dish = meal?.parts?.[partType];
                    if (!dish) return null;
                    const key = dishKey(day.day, mealType, partType, dish.name);
                    const isFixed = fixedDishKeys.includes(key);
                    return (
                      <div className="dish-tile" key={`${day.day}-${mealType}-${partType}`}>
                        <div>
                          <span>{partLabel}</span>
                          <strong>{dish.name}</strong>
                        </div>
                        <p>
                          {dish.meta?.cook_time_minutes || 25} {T.minutes} · {T.difficulty} {stars(dish.meta?.difficulty)}
                        </p>
                        {dish.reasons?.length ? (
                          <div className="reason-list">
                            {dish.reasons.map((reason) => <span key={reason}>{reason}</span>)}
                          </div>
                        ) : null}
                        <div className="dish-actions">
                          <button onClick={() => onInspect(dish.name)}><Eye size={15} /> {T.view}</button>
                          <button className={isFixed ? "active" : ""} onClick={() => onToggleFixed(key)}><Pin size={15} /> {isFixed ? T.fixed : T.fix}</button>
                          <button disabled={isFixed} onClick={() => onReplace(day.day, mealType, partType)}><RefreshCw size={15} /> {T.replace}</button>
                          <button disabled={isFixed} onClick={() => onReplace(day.day, mealType, partType, "\u6e05\u6de1")}><RefreshCw size={15} /> {T.replaceLight}</button>
                          <button disabled={isFixed} onClick={() => onReplace(day.day, mealType, partType, "\u5feb\u624b")}><RefreshCw size={15} /> {T.replaceFast}</button>
                          <button disabled={isFixed} onClick={() => onReplace(day.day, mealType, partType, "\u7d20\u83dc")}><RefreshCw size={15} /> {T.replaceVeg}</button>
                          <button disabled={isFixed} onClick={() => onReplace(day.day, mealType, partType, "\u9ad8\u86cb\u767d \u8089")}><RefreshCw size={15} /> {T.replaceProtein}</button>
                          <button disabled={isFixed} onClick={() => onRemove(day.day, mealType, partType)}><Trash2 size={15} /> {T.remove}</button>
                        </div>
                      </div>
                    );
                  })}
                </div>
                {meal?.timeline?.length ? (
                  <div className="timeline-block">
                    <span>{T.timeline}</span>
                    <div className="timeline-track">
                      {meal.timeline.map((item) => (
                        <div className="timeline-item" key={`${day.day}-${mealType}-${item.offset_minutes}-${item.title}`}>
                          <strong>T+{item.offset_minutes}</strong>
                          <p>{item.title}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </section>
            );
          })}
        </article>
      ))}
    </div>
  );
}

function renderPlanLine(line, index) {
  if (line.startsWith("# ")) return null;
  if (line.startsWith("## ")) return <h3 key={index}>{line.replace(/^##\s*/, "")}</h3>;
  if (line.startsWith("### ")) return <h4 key={index}>{line.replace(/^###\s*/, "")}</h4>;
  if (line.startsWith("#### ")) return <h5 key={index}>{line.replace(/^####\s*/, "")}</h5>;
  if (line.startsWith("- \u96be\u5ea6")) return <p className="metric" key={index}><Star size={15} /> {line.replace(/^- /, "")}</p>;
  if (line.startsWith("- \u9884\u8ba1\u65f6\u95f4") || line.startsWith("- \u672c\u9910\u9884\u8ba1\u8017\u65f6")) {
    return <p className="metric" key={index}><Clock3 size={15} /> {line.replace(/^- /, "")}</p>;
  }
  if (line.startsWith("- \u63a8\u8350\u8bc4\u5206")) return <p className="metric" key={index}><Sparkles size={15} /> {line.replace(/^- /, "")}</p>;
  if (line.startsWith("- ")) return <p className="meta-line" key={index}>{line.replace(/^- /, "")}</p>;
  if (line.trim()) return <p key={index}>{line}</p>;
  return null;
}

function MealPlanView({ artifacts, onInspect, onReplace, onRemove, onRerollMeal, onRerollDay, fixedDishKeys, onToggleFixed }) {
  const sections = useMemo(() => splitPlan(artifacts.mealPlanMarkdown), [artifacts.mealPlanMarkdown]);
  const hasMenu = artifacts.menu?.length;
  return (
    <section className="panel plan-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Meal Plan</p>
          <h2><ChefHat size={22} /> {T.mealPlan}</h2>
        </div>
      </div>

      <div className="plan-scroll">
        {hasMenu ? (
          <MenuEditor
            menu={artifacts.menu}
            onInspect={onInspect}
            onReplace={onReplace}
            onRemove={onRemove}
            onRerollMeal={onRerollMeal}
            onRerollDay={onRerollDay}
            fixedDishKeys={fixedDishKeys}
            onToggleFixed={onToggleFixed}
          />
        ) : sections.length ? (
          sections.slice(0, 14).map((section, index) => (
            <article className="meal-card" key={index}>
              {section.split("\n").map(renderPlanLine)}
            </article>
          ))
        ) : (
          <div className="empty-state">
            <ChefHat size={34} />
            <h3>{T.noMenu}</h3>
            <p>{T.noMenuHint}</p>
          </div>
        )}
      </div>
    </section>
  );
}

function RecipeBrowser({
  recipes,
  selectedNames,
  setSelectedNames,
  shopping,
  expiringPantry,
  activeRecipeName,
  setActiveRecipeName,
  favoriteRecipes,
  onToggleFavorite,
  blacklistedRecipes,
  onToggleBlacklist,
  checkedItems,
  setCheckedItems,
}) {
  const [query, setQuery] = useState("");
  const [selectedOnly, setSelectedOnly] = useState(false);
  const [hideBlacklisted, setHideBlacklisted] = useState(true);
  const [expiringOnly, setExpiringOnly] = useState(false);
  const expiringNames = useMemo(() => (expiringPantry || []).map((item) => item.name).filter(Boolean), [expiringPantry]);
  const filtered = useMemo(() => {
    const q = query.trim();
    return recipes
      .filter((recipe) => !hideBlacklisted || !blacklistedRecipes.includes(recipe.name))
      .filter((recipe) => !selectedOnly || selectedNames.includes(recipe.name))
      .filter((recipe) => !expiringOnly || Object.keys(recipe.ingredients || {}).some((name) => expiringNames.some((stock) => stock === name || stock.includes(name) || name.includes(stock))))
      .filter((recipe) => !q || recipe.name.includes(q))
      .slice(0, 80);
  }, [recipes, query, selectedNames, selectedOnly, hideBlacklisted, blacklistedRecipes, expiringOnly, expiringNames]);
  const active = recipes.find((recipe) => recipe.name === activeRecipeName) || filtered[0];
  const isFavorite = active ? favoriteRecipes.includes(active.name) : false;
  const isBlacklisted = active ? blacklistedRecipes.includes(active.name) : false;

  function toggle(name) {
    setSelectedNames((prev) => (prev.includes(name) ? prev.filter((item) => item !== name) : [...prev, name]));
  }

  return (
    <section className="recipe-layout">
      <div className="panel recipe-list-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Recipes</p>
            <h2><BookOpen size={21} /> {T.recipeLibrary}</h2>
          </div>
        </div>
        <input className="search-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={T.searchRecipe} />
        <div className="recipe-tools">
          <button className={selectedOnly ? "tool-chip active" : "tool-chip"} onClick={() => setSelectedOnly((value) => !value)}>
            {T.selectedOnly}
          </button>
          <button className={hideBlacklisted ? "tool-chip active" : "tool-chip"} onClick={() => setHideBlacklisted((value) => !value)}>
            {T.hideBlacklisted}
          </button>
          {expiringNames.length ? (
            <button className={expiringOnly ? "tool-chip active" : "tool-chip"} onClick={() => setExpiringOnly((value) => !value)}>
              {T.expiringOnly}
            </button>
          ) : null}
          <button className="tool-chip" onClick={() => setSelectedNames([])}>
            {T.clearSelected}
          </button>
        </div>
        <div className="recipe-list">
          {filtered.map((recipe) => (
            <button
              className={active?.name === recipe.name ? "recipe-row active" : "recipe-row"}
              key={recipe.name}
              onClick={() => setActiveRecipeName(recipe.name)}
            >
              <span>{recipe.name}</span>
              <em>{favoriteRecipes.includes(recipe.name) ? "\u2665 " : ""}{recipe.meta?.cook_time_minutes || 25} {T.minutes}</em>
            </button>
          ))}
        </div>
      </div>

      <div className="panel recipe-detail-panel">
        {active ? (
          <>
            <div className="panel-header">
              <div>
                <p className="eyebrow">Recipe Detail</p>
                <h2><ChefHat size={22} /> {active.name}</h2>
              </div>
              <button className={selectedNames.includes(active.name) ? "select-action selected" : "select-action"} onClick={() => toggle(active.name)}>
                {selectedNames.includes(active.name) ? T.selected : T.addToList}
              </button>
            </div>
            <div className="recipe-metrics">
              <IconBadge icon={Clock3}>{active.meta?.cook_time_minutes || 25} {T.minutes}</IconBadge>
              <IconBadge icon={Star}>{T.difficulty} {stars(active.meta?.difficulty)}</IconBadge>
              <IconBadge icon={Sparkles}>{active.meta?.score || 4.0}/5</IconBadge>
            </div>
            <div className="recipe-preference-actions">
              <button className={isFavorite ? "active" : ""} onClick={() => onToggleFavorite(active.name)}><Heart size={15} /> {isFavorite ? T.favorited : T.favorite}</button>
              <button className={isBlacklisted ? "danger active" : "danger"} onClick={() => onToggleBlacklist(active.name)}><Ban size={15} /> {isBlacklisted ? T.blacklisted : T.blacklist}</button>
            </div>
            <div className="detail-columns">
              <section>
                <h3>{T.ingredients}</h3>
                <ul className="ingredient-list">
                  {Object.entries(active.ingredients || {}).map(([name, qty]) => (
                    <li key={name}><span>{name}</span><em>{qty}</em></li>
                  ))}
                </ul>
              </section>
              <section>
                <h3>{T.steps}</h3>
                <ol className="steps-list">
                  {cleanRecipeSteps(active.steps).map((step, index) => (
                    <li key={`${active.name}-${index}`}>{step}</li>
                  ))}
                </ol>
              </section>
            </div>
          </>
        ) : (
          <div className="empty-state">{T.noRecipes}</div>
        )}
      </div>

      <div className="panel compact">
        <p className="eyebrow">Selected Shopping</p>
        <h2><ShoppingBag size={21} /> {T.selectedShopping}</h2>
        <p className="muted">{selectedNames.length ? `${T.selected} ${selectedNames.length} \u9053\u83dc` : T.selectedHint}</p>
        {selectedNames.length ? (
          <div className="selected-tags">
            {selectedNames.map((name) => (
              <button key={name} onClick={() => toggle(name)}>
                {name}
              </button>
            ))}
          </div>
        ) : null}
        <ShoppingList shopping={shopping} checkedItems={checkedItems} setCheckedItems={setCheckedItems} />
      </div>
    </section>
  );
}

function PantryPage({ pantryItems, pantryForm, setPantryForm, onAddPantry, onDeletePantry }) {
  function update(key, value) {
    setPantryForm((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <section className="pantry-layout">
      <div className="panel form-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Pantry</p>
            <h2><PackagePlus size={21} /> {T.addPantry}</h2>
          </div>
          <button className="primary-action" onClick={onAddPantry}>
            <PackagePlus size={17} />
            {T.addPantry}
          </button>
        </div>
        <p className="form-note">{T.pantryHint}</p>
        <div className="form-grid pantry-form-grid">
          <Field label={T.pantryName}>
            <input value={pantryForm.name} onChange={(e) => update("name", e.target.value)} placeholder="\u9e21\u86cb" />
          </Field>
          <Field label={T.quantity}>
            <input type="number" min="0" value={pantryForm.quantity} onChange={(e) => update("quantity", e.target.value)} />
          </Field>
          <Field label={T.unit}>
            <input value={pantryForm.unit} onChange={(e) => update("unit", e.target.value)} placeholder="\u4e2a/g/\u65a4" />
          </Field>
          <Field label={T.category}>
            <select value={pantryForm.category} onChange={(e) => update("category", e.target.value)}>
              {["\u852c\u83dc", "\u8089\u86cb\u5976", "\u4e3b\u98df", "\u8c03\u6599", "\u6c34\u679c", "\u5176\u4ed6"].map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </Field>
          <Field label={T.expiryDate}>
            <input type="date" value={pantryForm.expiry_date || ""} onChange={(e) => update("expiry_date", e.target.value)} />
          </Field>
        </div>
      </div>

      <div className="panel compact pantry-list-panel">
        <p className="eyebrow">Current Pantry</p>
        <h2><Utensils size={21} /> {T.pantry}</h2>
        {pantryItems.length ? (
          <ul className="pantry-list">
            {pantryItems.map((item) => {
              const state = expiryState(item.expiry_date);
              return (
              <li className={state ? `expiry-${state}` : ""} key={item.name}>
                <div>
                  <strong>{item.name}</strong>
                  <span>{item.category}</span>
                  {item.expiry_date ? (
                    <small>
                      {T.expiryDate}: {item.expiry_date}
                      {state === "soon" ? ` · ${T.expiringSoon}` : ""}
                      {state === "expired" ? ` · ${T.expired}` : ""}
                    </small>
                  ) : null}
                </div>
                <em>{item.quantity}{item.unit}</em>
                <button onClick={() => onDeletePantry(item.name)}><Trash2 size={15} /> {T.remove}</button>
              </li>
              );
            })}
          </ul>
        ) : (
          <p className="muted">{T.pantryHint}</p>
        )}
      </div>
    </section>
  );
}

function ChatPanel({ messages, input, setInput, onSend, loading }) {
  return (
    <section className="panel chat-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Qwen Agent</p>
          <h2><MessageCircle size={21} /> {T.chatTitle}</h2>
        </div>
        <span className={loading ? "status busy" : "status"}>{loading ? T.thinking : T.online}</span>
      </div>

      <div className="messages">
        {messages.map((msg, index) => (
          <div className={`message ${msg.role}`} key={`${msg.role}-${index}`}>
            <span>{msg.role === "user" ? T.you : "Agent"}</span>
            <p>{msg.content}</p>
          </div>
        ))}
      </div>

      <div className="quick-prompts">
        {quickPrompts.map((prompt) => (
          <button key={prompt} type="button" onClick={() => setInput(prompt)} disabled={loading}>
            {prompt}
          </button>
        ))}
      </div>

      <form className="composer" onSubmit={(event) => { event.preventDefault(); onSend(); }}>
        <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="\u4e5f\u53ef\u4ee5\u76f4\u63a5\u8bf4\uff1a\u4e00\u8364\u4e24\u7d20\uff0c\u9884\u7b97150\uff0c\u751f\u6210" />
        <button disabled={loading || !input.trim()} type="submit" title={T.send}>
          <Send size={18} />
          {T.send}
        </button>
      </form>
    </section>
  );
}

function ShoppingList({ shopping, checkedItems, setCheckedItems }) {
  const [collapsed, setCollapsed] = useState([]);
  const [hideDone, setHideDone] = useState(false);
  const items = shoppingItems(shopping);
  const categories = shopping?.categories || {};
  const grouped = Object.keys(categories).length
    ? Object.entries(categories).map(([category, names]) => [
        category,
        names.map((name) => [name, (shopping?.items || {})[name] || "\u9002\u91cf/\u6309\u9700"]),
      ])
    : [["\u5176\u4ed6", items]];
  if (!items.length) return <p className="muted">{T.shoppingEmpty}</p>;
  return (
    <div className="shopping-groups">
      <button className={hideDone ? "tool-chip active" : "tool-chip"} onClick={() => setHideDone((value) => !value)}>
        {T.hideDone}
      </button>
      {grouped.map(([category, categoryItems]) => {
        const visibleItems = hideDone ? categoryItems.filter(([name]) => !checkedItems.includes(name)) : categoryItems;
        const isCollapsed = collapsed.includes(category);
        if (!visibleItems.length && hideDone) return null;
        return (
          <section className="shopping-category" key={category}>
            <button className="category-header" onClick={() => toggleStoredItem(collapsed, setCollapsed, category)}>
              <span>{category}</span>
              <em>{visibleItems.length}</em>
            </button>
            {!isCollapsed ? (
              <ul className="shopping-list checkable">
                {visibleItems.map(([name, qty]) => {
                  const checked = checkedItems.includes(name);
                  return (
                    <li className={checked ? "checked" : ""} key={name}>
                      <label>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleStoredItem(checkedItems, setCheckedItems, name)}
                        />
                        <span>{name}</span>
                      </label>
                      <em>{qty}</em>
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}

function MenuHistory({ history, onRestore, onInspect }) {
  return (
    <section className="panel compact">
      <div className="panel-header tight">
        <div>
          <p className="eyebrow">History</p>
          <h2><Clock3 size={21} /> {T.menuHistory}</h2>
        </div>
      </div>
      {history.length ? (
        <div className="history-list">
          {history.slice(0, 6).map((item) => (
            <button key={item.id} onClick={() => onInspect(item)}>
              <span>{item.title}</span>
              <em>{item.createdAt}</em>
              <strong>{T.viewDetail}</strong>
            </button>
          ))}
        </div>
      ) : (
        <p className="muted">{T.noHistory}</p>
      )}
    </section>
  );
}

function FavoriteMenuList({ favorites, onRestore, onInspect }) {
  return (
    <section className="panel compact">
      <div className="panel-header tight">
        <div>
          <p className="eyebrow">Saved</p>
          <h2><Heart size={21} /> {T.favoriteMenus}</h2>
        </div>
      </div>
      {favorites.length ? (
        <div className="history-list">
          {favorites.slice(0, 6).map((item) => (
            <button key={item.id} onClick={() => onInspect(item)}>
              <span>{item.title}</span>
              <em>{item.createdAt}</em>
              <strong>{T.viewDetail}</strong>
            </button>
          ))}
        </div>
      ) : (
        <p className="muted">{T.noFavoriteMenus}</p>
      )}
    </section>
  );
}

function SidePanel({ artifacts, checkedItems, setCheckedItems, menuHistory, favoriteMenus, onRestoreHistory, onInspectHistory, onFavoriteMenu }) {
  const prefs = artifacts.prefs || {};
  return (
    <aside className="side-stack">
      <section className="panel compact">
        <p className="eyebrow">{T.preference}</p>
        <div className="export-actions">
          <button onClick={() => downloadText("meal_plan.md", artifacts.mealPlanMarkdown || "")}><Download size={15} /> {T.exportMenu}</button>
          <button onClick={() => downloadText("shopping_list.json", JSON.stringify(artifacts.shoppingList || {}, null, 2), "application/json;charset=utf-8")}><Download size={15} /> {T.exportShopping}</button>
          <button onClick={onFavoriteMenu}><Heart size={15} /> {T.favoriteMenu}</button>
        </div>
        <div className="stats-grid">
          <Stat icon={ChefHat} label={T.people} value={prefs.people || "-"} />
          <Stat icon={ListChecks} label={T.days} value={prefs.days || "-"} />
          <Stat icon={ShoppingBag} label={T.budget} value={prefs.budget ? `¥${prefs.budget}` : "-"} />
          <Stat icon={Sparkles} label={T.cuisine} value={prefs.cuisine || "-"} />
          <Stat icon={Utensils} label={T.dishCount} value={prefs.dish_count ? `${prefs.dish_count}\u9053` : "-"} />
          <Stat icon={Leaf} label="\u8364\u7d20" value={prefs.meat_count != null || prefs.vegetable_count != null ? `${prefs.meat_count ?? "-"}\u8364${prefs.vegetable_count ?? "-"}\u7d20` : "-"} />
        </div>
      </section>

      <section className="panel compact">
        <div className="panel-header tight">
          <div>
            <p className="eyebrow">Shopping</p>
            <h2><ShoppingBag size={21} /> {T.allShopping}</h2>
          </div>
        </div>
        <ShoppingList shopping={artifacts.shoppingList} checkedItems={checkedItems} setCheckedItems={setCheckedItems} />
      </section>

      <MenuHistory history={menuHistory} onRestore={onRestoreHistory} onInspect={onInspectHistory} />
      <FavoriteMenuList favorites={favoriteMenus} onRestore={onRestoreHistory} onInspect={onInspectHistory} />
    </aside>
  );
}

function MiniProgramView({
  artifacts,
  loading,
  onGenerate,
  onFavoriteMenu,
  menuHistory,
  favoriteMenus,
  onInspectHistory,
  onRestoreHistory,
  checkedItems,
  setCheckedItems,
  setActiveView,
}) {
  const prefs = artifacts.prefs || {};
  return (
    <section className="mini-shell">
      <div className="mini-hero">
        <p className="eyebrow">Mini App</p>
        <h2>{T.appTitle}</h2>
        <p>{prefs.people ? `${prefs.people}\u4eba · ${prefs.days || 1}\u5929 · ${prefs.cuisine || T.home}` : T.noMenuHint}</p>
        <div className="mini-actions">
          <button className="primary-action" onClick={onGenerate} disabled={loading}>
            <Sparkles size={17} />
            {loading ? T.generating : T.generate}
          </button>
          <button className="select-action" onClick={onFavoriteMenu}>
            <Heart size={16} />
            {T.favoriteMenu}
          </button>
        </div>
      </div>

      <div className="mini-grid">
        <section className="mini-card">
          <div className="mini-card-head">
            <span>{T.currentMenu}</span>
            <button onClick={() => setActiveView("plan")}>{T.view}</button>
          </div>
          <CompactDishList menu={artifacts.menu} />
        </section>

        <section className="mini-card">
          <div className="mini-card-head">
            <span>{T.expiringTitle}</span>
            <button onClick={() => setActiveView("pantry")}>{T.view}</button>
          </div>
          <div className="expiring-items mini-expiring">
            {(artifacts.expiringPantry || []).slice(0, 5).map((item) => (
              <span className={item.status === "expired" ? "expired" : ""} key={`${item.name}-${item.expiry_date}`}>
                {item.name}
                <em>{item.days_left < 0 ? T.expired : `${item.days_left}\u5929`}</em>
              </span>
            ))}
            {!(artifacts.expiringPantry || []).length ? <p className="muted">{T.pantryHint}</p> : null}
          </div>
        </section>

        <section className="mini-card">
          <div className="mini-card-head">
            <span>{T.allShopping}</span>
            <button onClick={() => setActiveView("plan")}>{T.view}</button>
          </div>
          <ShoppingList shopping={artifacts.shoppingList} checkedItems={checkedItems} setCheckedItems={setCheckedItems} />
        </section>

        <section className="mini-card">
          <div className="mini-card-head">
            <span>{T.menuHistory}</span>
            <button onClick={() => setActiveView("plan")}>{T.view}</button>
          </div>
          <div className="history-list mini-history">
            {[...favoriteMenus.slice(0, 2), ...menuHistory.slice(0, 3)].map((item) => (
              <button key={`mini-${item.id}`} onClick={() => onInspectHistory(item)}>
                <span>{item.title}</span>
                <em>{item.createdAt}</em>
                <strong>{T.viewDetail}</strong>
              </button>
            ))}
            {!favoriteMenus.length && !menuHistory.length ? <p className="muted">{T.noHistory}</p> : null}
          </div>
        </section>
      </div>
    </section>
  );
}

function App() {
  const [activeView, setActiveView] = useState("plan");
  const [form, setForm] = useState(initialPrefs);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [artifacts, setArtifacts] = useState({});
  const [recipes, setRecipes] = useState([]);
  const [selectedNames, setSelectedNames] = useState([]);
  const [selectedShopping, setSelectedShopping] = useState({});
  const [activeRecipeName, setActiveRecipeName] = useState("");
  const [pantryItems, setPantryItems] = useState([]);
  const [pantryForm, setPantryForm] = useState({ name: "", quantity: 1, unit: "\u4efd", category: "\u5176\u4ed6", expiry_date: "" });
  const [notice, setNotice] = useState(null);
  const [detailItem, setDetailItem] = useState(null);
  const [menuHistory, setMenuHistory] = useStoredJson("mealPlanner.menuHistory", []);
  const [favoriteMenus, setFavoriteMenus] = useStoredJson("mealPlanner.favoriteMenus", []);
  const [checkedShoppingItems, setCheckedShoppingItems] = useStoredList("mealPlanner.checkedShoppingItems");
  const [fixedDishKeys, toggleFixedDish, setFixedDishKeys] = useStoredList("mealPlanner.fixedDishKeys");
  const [favoriteRecipes, toggleFavoriteRecipe] = useStoredList("mealPlanner.favoriteRecipes");
  const [blacklistedRecipes, toggleBlacklistedRecipe] = useStoredList("mealPlanner.blacklistedRecipes");
  const [messages, setMessages] = useState([
    {
      role: "agent",
      content: "\u4f60\u597d\uff0c\u6211\u53ef\u4ee5\u5e2e\u4f60\u89c4\u5212\u83dc\u5355\u3001\u67e5\u770b\u505a\u6cd5\u3001\u751f\u6210\u8d2d\u7269\u6e05\u5355\u3002\u4f60\u53ef\u4ee5\u586b\u8868\u751f\u6210\uff0c\u4e5f\u53ef\u4ee5\u76f4\u63a5\u548c\u6211\u8bf4\u9700\u6c42\u3002",
    },
  ]);

  useEffect(() => {
    fetch(`${API_BASE}/api/state`)
      .then((res) => res.json())
      .then((data) => {
        setArtifacts(data.artifacts || {});
        setRecipes(data.recipes || []);
        setPantryItems(data.artifacts?.pantry || []);
      })
      .catch(() => setNotice({ type: "error", message: "\u540e\u7aef\u672a\u8fde\u63a5\uff0c\u8bf7\u5148\u542f\u52a8 FastAPI \u670d\u52a1\u3002" }));
  }, []);

  useEffect(() => {
    if (!selectedNames.length) {
      setSelectedShopping({});
      return;
    }
    fetch(`${API_BASE}/api/recipes/shopping`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ names: selectedNames }),
    })
      .then((res) => res.json())
      .then((data) => setSelectedShopping(data.items || {}))
      .catch(() => setNotice({ type: "error", message: "\u83dc\u54c1\u8d2d\u7269\u6e05\u5355\u83b7\u53d6\u5931\u8d25\u3002" }));
  }, [selectedNames]);

  async function readJsonResponse(res) {
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
  }

  function makeMenuRecord(nextArtifacts, idPrefix = "history") {
    if (!nextArtifacts?.menu?.length) return;
    const prefs = nextArtifacts.prefs || {};
    const title = `${prefs.days || 1}\u5929\u83dc\u5355 · ${prefs.people || "-"}\u4eba · ${new Date().toLocaleString()}`;
    return {
      id: `${idPrefix}-${Date.now()}`,
      title,
      createdAt: new Date().toLocaleString(),
      artifacts: {
        mealPlanMarkdown: nextArtifacts.mealPlanMarkdown,
        shoppingList: nextArtifacts.shoppingList,
        optimizedShoppingList: nextArtifacts.optimizedShoppingList,
        nutritionReportMarkdown: nextArtifacts.nutritionReportMarkdown,
        prefs: nextArtifacts.prefs,
        menu: nextArtifacts.menu,
        pantry: nextArtifacts.pantry,
        expiringPantry: nextArtifacts.expiringPantry,
      },
    };
  }

  function saveMenuHistory(nextArtifacts) {
    const record = makeMenuRecord(nextArtifacts);
    if (!record) return;
    setMenuHistory((prev) => [record, ...prev.filter((item) => item.id !== record.id)].slice(0, 8));
  }

  function restoreMenuHistory(item) {
    setArtifacts(item.artifacts || {});
    setPantryItems(item.artifacts?.pantry || pantryItems);
    setCheckedShoppingItems([]);
    setActiveView("plan");
    setDetailItem(null);
    setNotice({ type: "success", message: "\u5df2\u6062\u590d\u5386\u53f2\u83dc\u5355\u3002" });
  }

  function favoriteCurrentMenu() {
    const record = makeMenuRecord(artifacts, "favorite");
    if (!record) {
      setNotice({ type: "error", message: "\u8fd8\u6ca1\u6709\u53ef\u6536\u85cf\u7684\u83dc\u5355\u3002" });
      return;
    }
    setFavoriteMenus((prev) => [record, ...prev].slice(0, 12));
    setNotice({ type: "success", message: "\u5df2\u6536\u85cf\u8fd9\u4efd\u83dc\u5355\u3002" });
  }

  async function onGenerate() {
    setLoading(true);
    const payload = {
      ...form,
      people: Number(form.people) || 2,
      days: Number(form.days) || 1,
      budget: form.budget === "" ? null : Number(form.budget),
      dish_count: form.dish_count === "" ? null : Number(form.dish_count),
      meat_count: form.meat_count === "" ? null : Number(form.meat_count),
      vegetable_count: form.vegetable_count === "" ? null : Number(form.vegetable_count),
      avoid: form.avoid.split(/[\uFF0C,\s]+/).map((item) => item.trim()).filter(Boolean),
      blacklist: blacklistedRecipes,
      favorites: favoriteRecipes,
    };
    try {
      const res = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await readJsonResponse(res);
      setArtifacts(data.artifacts || {});
      setRecipes(data.recipes || recipes);
      setPantryItems(data.artifacts?.pantry || pantryItems);
      saveMenuHistory(data.artifacts || {});
      setCheckedShoppingItems([]);
      setFixedDishKeys([]);
      setNotice({ type: "success", message: "\u83dc\u5355\u5df2\u751f\u6210\u5e76\u4fdd\u5b58\u5230\u5386\u53f2\u3002" });
      setMessages((prev) => [...prev, { role: "agent", content: "\u8868\u5355\u83dc\u5355\u5df2\u7ecf\u751f\u6210\uff0c\u53ef\u4ee5\u76f4\u63a5\u67e5\u770b\u3001\u6362\u83dc\u6216\u8fdb\u5165\u83dc\u54c1\u9875\u770b\u505a\u6cd5\u3002" }]);
    } catch (error) {
      setNotice({ type: "error", message: `\u751f\u6210\u83dc\u5355\u5931\u8d25\uff1a${error.message}` });
    } finally {
      setLoading(false);
    }
  }

  async function onReplace(day, mealType, partType, constraint = null) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/menu/replace`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ day, meal_type: mealType, part_type: partType, constraint }),
      });
      const data = await readJsonResponse(res);
      setArtifacts(data.artifacts || {});
      setRecipes(data.recipes || recipes);
      setPantryItems(data.artifacts?.pantry || pantryItems);
      setMessages((prev) => [...prev, { role: "agent", content: data.reply || "\u5df2\u6362\u83dc\u5e76\u66f4\u65b0\u8d2d\u7269\u6e05\u5355\u3002" }]);
    } catch (error) {
      setNotice({ type: "error", message: `\u6362\u83dc\u5931\u8d25\uff1a${error.message}` });
    } finally {
      setLoading(false);
    }
  }

  async function onRemove(day, mealType, partType) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/menu/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ day, meal_type: mealType, part_type: partType }),
      });
      const data = await readJsonResponse(res);
      setArtifacts(data.artifacts || {});
      setRecipes(data.recipes || recipes);
      setPantryItems(data.artifacts?.pantry || pantryItems);
      setMessages((prev) => [...prev, { role: "agent", content: data.reply || "\u5df2\u5220\u9664\u5e76\u66f4\u65b0\u8d2d\u7269\u6e05\u5355\u3002" }]);
    } catch (error) {
      setNotice({ type: "error", message: `\u5220\u9664\u83dc\u54c1\u5931\u8d25\uff1a${error.message}` });
    } finally {
      setLoading(false);
    }
  }

  async function onRerollMeal(day, mealType) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/menu/reroll-meal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ day, meal_type: mealType, fixed_keys: fixedDishKeys }),
      });
      const data = await readJsonResponse(res);
      setArtifacts(data.artifacts || {});
      setRecipes(data.recipes || recipes);
      setPantryItems(data.artifacts?.pantry || pantryItems);
      setMessages((prev) => [...prev, { role: "agent", content: data.reply || "\u5df2\u91cd\u6392\u8fd9\u9910\u3002" }]);
    } catch (error) {
      setNotice({ type: "error", message: `\u91cd\u6392\u8fd9\u9910\u5931\u8d25\uff1a${error.message}` });
    } finally {
      setLoading(false);
    }
  }

  async function onRerollDay(day) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/menu/reroll-day`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ day, fixed_keys: fixedDishKeys }),
      });
      const data = await readJsonResponse(res);
      setArtifacts(data.artifacts || {});
      setRecipes(data.recipes || recipes);
      setPantryItems(data.artifacts?.pantry || pantryItems);
      setMessages((prev) => [...prev, { role: "agent", content: data.reply || "\u5df2\u91cd\u6392\u8fd9\u5929\u3002" }]);
    } catch (error) {
      setNotice({ type: "error", message: `\u91cd\u6392\u8fd9\u5929\u5931\u8d25\uff1a${error.message}` });
    } finally {
      setLoading(false);
    }
  }

  async function onAddPantry() {
    const name = pantryForm.name.trim();
    if (!name) return;
    try {
      const res = await fetch(`${API_BASE}/api/pantry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...pantryForm,
          name,
          quantity: Number(pantryForm.quantity) || 1,
        }),
      });
      const data = await readJsonResponse(res);
      setPantryItems(data.items || []);
      setArtifacts(data.artifacts || artifacts);
      setPantryForm((prev) => ({ ...prev, name: "", quantity: 1, expiry_date: "" }));
      setNotice({ type: "success", message: "\u5e93\u5b58\u5df2\u66f4\u65b0\u3002" });
    } catch (error) {
      setNotice({ type: "error", message: `\u6dfb\u52a0\u5e93\u5b58\u5931\u8d25\uff1a${error.message}` });
    }
  }

  async function onDeletePantry(name) {
    try {
      const res = await fetch(`${API_BASE}/api/pantry/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const data = await readJsonResponse(res);
      setPantryItems(data.items || []);
      setArtifacts(data.artifacts || artifacts);
      setNotice({ type: "success", message: "\u5df2\u5220\u9664\u5e93\u5b58\u98df\u6750\u3002" });
    } catch (error) {
      setNotice({ type: "error", message: `\u5220\u9664\u5e93\u5b58\u5931\u8d25\uff1a${error.message}` });
    }
  }

  function inspectRecipe(name) {
    setActiveRecipeName(name);
    setActiveView("recipes");
  }

  async function onSend() {
    const message = input.trim();
    if (!message) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await readJsonResponse(res);
      setMessages((prev) => [...prev, { role: "agent", content: data.reply || "\u5df2\u5904\u7406\u3002" }]);
      setArtifacts(data.artifacts || {});
      if (data.artifacts?.menu?.length) {
        saveMenuHistory(data.artifacts);
      }
    } catch (error) {
      const message = `\u540e\u7aef\u8bf7\u6c42\u5931\u8d25\uff1a${error.message}`;
      setNotice({ type: "error", message });
      setMessages((prev) => [...prev, { role: "agent", content: message }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Local Meal Intelligence</p>
          <h1>{T.appTitle}</h1>
        </div>
        <div className="top-actions">
          <IconBadge icon={Sparkles}>React + Vite</IconBadge>
          <IconBadge icon={ChefHat}>FastAPI</IconBadge>
        </div>
      </header>

      <NoticeBar notice={notice} onClose={() => setNotice(null)} />

      <nav className="view-tabs">
        <button className={activeView === "mini" ? "active" : ""} onClick={() => setActiveView("mini")}><Sparkles size={17} /> {T.mini}</button>
        <button className={activeView === "plan" ? "active" : ""} onClick={() => setActiveView("plan")}><ListChecks size={17} /> {T.plan}</button>
        <button className={activeView === "recipes" ? "active" : ""} onClick={() => setActiveView("recipes")}><BookOpen size={17} /> {T.recipes}</button>
        <button className={activeView === "pantry" ? "active" : ""} onClick={() => setActiveView("pantry")}><PackagePlus size={17} /> {T.pantry}</button>
        <button className={activeView === "chat" ? "active" : ""} onClick={() => setActiveView("chat")}><MessageCircle size={17} /> {T.assistant}</button>
      </nav>

      {activeView === "mini" && (
        <MiniProgramView
          artifacts={artifacts}
          loading={loading}
          onGenerate={onGenerate}
          onFavoriteMenu={favoriteCurrentMenu}
          menuHistory={menuHistory}
          favoriteMenus={favoriteMenus}
          onInspectHistory={setDetailItem}
          onRestoreHistory={restoreMenuHistory}
          checkedItems={checkedShoppingItems}
          setCheckedItems={setCheckedShoppingItems}
          setActiveView={setActiveView}
        />
      )}

      {activeView === "plan" && (
        <div className="planning-page">
          <ExpiringPantryAlert items={artifacts.expiringPantry} onGenerate={onGenerate} loading={loading} />
          <PlanningForm
            form={form}
            setForm={setForm}
            onGenerate={onGenerate}
            loading={loading}
            blacklistedCount={blacklistedRecipes.length}
            favoriteCount={favoriteRecipes.length}
          />
          <div className="workspace">
            <MealPlanView
              artifacts={artifacts}
              onInspect={inspectRecipe}
              onReplace={onReplace}
              onRemove={onRemove}
              onRerollMeal={onRerollMeal}
              onRerollDay={onRerollDay}
              fixedDishKeys={fixedDishKeys}
              onToggleFixed={toggleFixedDish}
            />
            <SidePanel
              artifacts={artifacts}
              checkedItems={checkedShoppingItems}
              setCheckedItems={setCheckedShoppingItems}
              menuHistory={menuHistory}
              favoriteMenus={favoriteMenus}
              onRestoreHistory={restoreMenuHistory}
              onInspectHistory={setDetailItem}
              onFavoriteMenu={favoriteCurrentMenu}
            />
          </div>
        </div>
      )}

      {activeView === "recipes" && (
        <RecipeBrowser
          recipes={recipes}
          selectedNames={selectedNames}
          setSelectedNames={setSelectedNames}
          shopping={selectedShopping}
          expiringPantry={artifacts.expiringPantry}
          activeRecipeName={activeRecipeName}
          setActiveRecipeName={setActiveRecipeName}
          favoriteRecipes={favoriteRecipes}
          onToggleFavorite={toggleFavoriteRecipe}
          blacklistedRecipes={blacklistedRecipes}
          onToggleBlacklist={toggleBlacklistedRecipe}
          checkedItems={checkedShoppingItems}
          setCheckedItems={setCheckedShoppingItems}
        />
      )}

      {activeView === "pantry" && (
        <PantryPage
          pantryItems={pantryItems}
          pantryForm={pantryForm}
          setPantryForm={setPantryForm}
          onAddPantry={onAddPantry}
          onDeletePantry={onDeletePantry}
        />
      )}

      {activeView === "chat" && (
        <ChatPanel messages={messages} input={input} setInput={setInput} onSend={onSend} loading={loading} />
      )}

      <MenuDetailModal item={detailItem} onClose={() => setDetailItem(null)} onRestore={restoreMenuHistory} />
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
