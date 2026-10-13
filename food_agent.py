# -*- coding: utf-8 -*-
"""
美食智能体 (Food Agent)
推理驱动: 本地 Ollama qwen3.5:0.8b + ReAct 循环 (Thought -> Action -> Observation -> Final Answer)
运行: python food_agent.py
"""
import json
import re
import sys
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:0.8b"
MAX_STEPS = 5  # ReAct 最大推理步数

# ---------------------------------------------------------------------------
# 本地工具 (智能体通过 Action 调用, 真实结果回填为 Observation)
# ---------------------------------------------------------------------------

RECIPES = {
    "番茄炒蛋": {
        "食材": ["番茄2个", "鸡蛋3个", "盐适量", "糖1勺", "食用油"],
        "步骤": ["鸡蛋打散加盐搅匀", "热油下蛋液炒至凝固盛出", "锅内下番茄块炒出汁", "加糖和盐, 倒回鸡蛋翻炒均匀出锅"],
        "难度": "简单", "耗时": "10分钟",
    },
    "宫保鸡丁": {
        "食材": ["鸡胸肉300克", "花生米50克", "干辣椒", "花椒", "姜蒜", "酱油", "醋", "糖", "淀粉"],
        "步骤": ["鸡丁用酱油淀粉腌制15分钟", "调碗汁: 酱油醋糖淀粉加水", "热油爆香花椒干辣椒", "下鸡丁滑炒变色", "倒碗汁和花生米翻匀"],
        "难度": "中等", "耗时": "25分钟",
    },
    "红烧肉": {
        "食材": ["五花肉500克", "冰糖30克", "生抽", "老抽", "料酒", "姜", "葱", "八角"],
        "步骤": ["五花肉切块焯水", "冰糖炒糖色", "下肉块翻炒上色", "加料酒生抽老抽和热水没过肉", "小火炖60分钟收汁"],
        "难度": "中等", "耗时": "90分钟",
    },
    "麻婆豆腐": {
        "食材": ["嫩豆腐1盒", "牛肉末50克", "豆瓣酱", "花椒粉", "辣椒面", "蒜苗", "淀粉"],
        "步骤": ["豆腐切块盐水焯烫", "炒香牛肉末加豆瓣酱", "加水下豆腐煮3分钟", "淀粉勾芡撒花椒粉蒜苗"],
        "难度": "简单", "耗时": "20分钟",
    },
    "北京烤鸭": {
        "食材": ["整鸭", "麦芽糖", "五香料"],
        "步骤": ["鸭身充气挂糖色", "晾皮后入果木炉烤制", "片皮配荷叶饼葱丝甜面酱"],
        "难度": "困难", "耗时": "数小时",
    },
    "清蒸鲈鱼": {
        "食材": ["鲈鱼1条", "姜丝", "葱丝", "蒸鱼豉油", "料酒"],
        "步骤": ["鱼抹料酒盐腌10分钟", "水开上锅蒸8分钟", "倒掉汁水铺葱姜丝", "淋热油和蒸鱼豉油"],
        "难度": "简单", "耗时": "20分钟",
    },
}

NUTRITION = {  # 每100克
    "番茄炒蛋": {"热量": "86千卡", "蛋白质": "5.6克", "脂肪": "6.2克", "碳水": "3.1克"},
    "宫保鸡丁": {"热量": "180千卡", "蛋白质": "14克", "脂肪": "10克", "碳水": "8克"},
    "红烧肉": {"热量": "478千卡", "蛋白质": "9克", "脂肪": "45克", "碳水": "6克"},
    "麻婆豆腐": {"热量": "130千卡", "蛋白质": "8克", "脂肪": "9克", "碳水": "6克"},
    "清蒸鲈鱼": {"热量": "105千卡", "蛋白质": "19克", "脂肪": "3克", "碳水": "0克"},
    "北京烤鸭": {"热量": "436千卡", "蛋白质": "17克", "脂肪": "38克", "碳水": "3克"},
}

CUISINES = {
    "川菜": ["麻婆豆腐", "宫保鸡丁", "水煮鱼", "回锅肉"],
    "粤菜": ["清蒸鲈鱼", "白切鸡", "虾饺", "煲仔饭"],
    "鲁菜": ["糖醋鲤鱼", "九转大肠", "葱烧海参"],
    "家常菜": ["番茄炒蛋", "青椒肉丝", "土豆炖牛肉", "蛋炒饭"],
}


def tool_search_recipe(keyword: str) -> str:
    """搜索菜谱: 按关键词模糊匹配菜名"""
    hits = [name for name in RECIPES if keyword.strip() in name or name in keyword]
    if not hits:  # 再宽松匹配一次
        hits = [name for name in RECIPES if any(c in name for c in keyword if '\u4e00' <= c <= '\u9fff')]
    if not hits:
        return f"未找到与“{keyword}”相关的菜谱。已有菜谱: {'、'.join(RECIPES)}"
    out = []
    for name in hits:
        r = RECIPES[name]
        out.append(f"{name} | 食材: {'、'.join(r['食材'])} | 步骤: {'; '.join(r['步骤'])} | 难度: {r['难度']} | 耗时: {r['耗时']}")
    return " || ".join(out)


def tool_nutrition(dish: str) -> str:
    """查询营养: 每100克热量与宏量营养"""
    for name, v in NUTRITION.items():
        if dish.strip() in name or name in dish:
            return f"{name}每100克: 热量{v['热量']}, 蛋白质{v['蛋白质']}, 脂肪{v['脂肪']}, 碳水{v['碳水']}"
    return f"未收录“{dish}”的营养数据。已收录: {'、'.join(NUTRITION)}"


def tool_recommend(taste: str) -> str:
    """按口味/菜系推荐菜品"""
    for cuisine, dishes in CUISINES.items():
        if taste.strip() in cuisine or cuisine in taste:
            return f"{cuisine}推荐: {'、'.join(dishes)}"
    for kw, dishes in [("辣", CUISINES["川菜"]), ("清淡", CUISINES["粤菜"]), ("家常", CUISINES["家常菜"]), ("简单", ["番茄炒蛋", "清蒸鲈鱼", "麻婆豆腐"])]:
        if kw in taste:
            return f"根据“{taste}”推荐: {'、'.join(dishes)}"
    return f"没有找到“{taste}”相关推荐。可选菜系: {'、'.join(CUISINES)}"


TOOLS = {
    "search_recipe": (tool_search_recipe, "搜索菜谱, 参数为菜名关键词, 例: search_recipe(番茄炒蛋)"),
    "nutrition": (tool_nutrition, "查询菜品营养, 参数为菜名, 例: nutrition(红烧肉)"),
    "recommend": (tool_recommend, "按口味或菜系推荐菜品, 参数为口味关键词, 例: recommend(辣味)"),
}


def run_tool(action_line: str) -> str:
    """解析并执行 Action: 工具名(参数), 返回 Observation 文本"""
    m = re.search(r"([A-Za-z_]+)\s*\(([^)]*)\)", action_line)
    if not m:
        return "错误: 无法解析Action, 请使用格式 Action: 工具名(参数)"
    name, arg = m.group(1).strip(), m.group(2).strip()
    if name not in TOOLS:
        return f"错误: 未知工具 {name}。可用工具: {', '.join(TOOLS)}"
    try:
        return TOOLS[name][0](arg)
    except Exception as e:
        return f"工具执行出错: {e}"


# ---------------------------------------------------------------------------
# 调用本地 qwen3.5:0.8b
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "你是美食助手智能体, 通过工具回答问题。严格按以下格式回复, 每次只输出一行:\n"
    "Action: 工具名(参数)\n"
    "或\n"
    "Final Answer: 给用户的最终回答\n\n"
    "可用工具:\n"
    + "\n".join(f"- {k}: {v[1]}" for k, v in TOOLS.items())
    + "\n\n规则:\n1. 需要菜谱用search_recipe, 需要营养用nutrition, 需要推荐用recommend。\n"
    "2. 信息足够后立即输出Final Answer, 不要重复调用工具。\n"
    "3. 只输出Action行或Final Answer行, 不要输出其他内容。\n"
    "4. Final Answer必须完全基于Observation的真实数据, 严禁编造Observation里没有的菜名、食材或数值。"
)


def ask_llm(messages: list) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0.1, "num_predict": 200},
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, payload, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["message"]["content"].strip()


# ---------------------------------------------------------------------------
# ReAct 推理循环
# ---------------------------------------------------------------------------

def solve(question: str, verbose: bool = True, with_trace: bool = False):
    """with_trace=True 时返回 (答案, 推理轨迹列表)"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}]
    trace = []
    tool_calls = []
    def finish(answer):
        trace.append({"type": "answer", "text": answer})
        return (answer, trace) if with_trace else answer

    for step in range(MAX_STEPS):
        out = ask_llm(messages)
        if verbose:
            print(f"  [模型输出] {out}")
        trace.append({"type": "model", "text": out})
        # 取第一行有效决策 (兼容省略 Action: 前缀的情况)
        decision = ""
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Final Answer"):
                decision = line
                break
            if line.startswith("Action"):
                decision = line
                break
            if re.match(r"^[A-Za-z_]+\s*\(.*\)$", line):
                decision = "Action: " + line
                break
        if not decision:
            # 模型没按格式来, 直接当作最终回答
            return finish(out)
        if decision.startswith("Final Answer"):
            answer = decision.split(":", 1)[-1].strip()
            # 未调用过工具就想直接回答 -> 智能体自动执行一次工具取真实数据, 防止编造
            if not tool_calls and step == 0:
                if re.search(r"热量|营养|卡|脂肪|蛋白|糖", question):
                    auto = f"Action: nutrition({question})"
                elif re.search(r"推荐|有什么|哪些菜|想吃|口味", question):
                    auto = f"Action: recommend({question})"
                else:
                    auto = f"Action: search_recipe({question})"
                observation = run_tool(auto)
                if verbose:
                    print(f"  [自动执行工具] {auto}\n  [工具返回] {observation}")
                tool_calls.append((auto, observation))
                trace.append({"type": "tool", "action": auto, "observation": observation, "auto": True})
                messages.append({"role": "assistant", "content": auto})
                messages.append({"role": "user", "content": f"Observation: {observation}\n请根据以上真实数据重新输出Final Answer:"})
                continue
            return finish(answer)
        # 执行工具
        observation = run_tool(decision)
        if verbose:
            print(f"  [工具返回] {observation}")
        tool_calls.append((decision, observation))
        trace.append({"type": "tool", "action": decision, "observation": observation, "auto": False})
        # 只回填真实 Observation, 防止模型自行编造
        messages.append({"role": "assistant", "content": decision})
        messages.append({"role": "user", "content": f"Observation: {observation}\n只能使用以上Observation中的数据, 不得编造其他菜品或数值。请输出Final Answer:"})
    return finish("推理步数已达上限, 请换个问题试试。")


def main():
    print("=" * 50)
    print("  美食智能体 (本地 qwen3.5:0.8b 推理驱动)")
    print("  输入问题开始对话, 输入 exit 退出")
    print("=" * 50)
    while True:
        try:
            q = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q.lower() in ("exit", "quit", "退出"):
            break
        print("智能体推理过程:")
        try:
            ans = solve(q)
        except Exception as e:
            print(f"  [错误] {e}")
            continue
        print(f"\n智能体: {ans}")


if __name__ == "__main__":
    if len(sys.argv) > 1:  # 非交互模式: python food_agent.py "问题"
        print(solve(" ".join(sys.argv[1:])))
    else:
        main()
