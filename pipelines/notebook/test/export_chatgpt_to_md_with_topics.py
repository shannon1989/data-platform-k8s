import json
import os
import re
from datetime import datetime
from pathlib import Path

INPUT_FILE = "conversations.json"
OUTPUT_DIR = "chatgpt-archive"

TOPIC_KEYWORDS = {
    "kafka": ["kafka", "offset", "consumer", "producer", "topic", "partition"],
    "spark": ["spark", "pyspark", "spark sql", "structured streaming"],
    "airflow": ["airflow", "dag", "task", "operator", "scheduler"],
    "k8s": ["kubernetes", "k8s", "pod", "deployment", "helm"],
    "clickhouse": ["clickhouse", "mergetree", "materialized view"],
    "web3": ["web3", "blockchain", "onchain"],
    "ethereum": ["ethereum", "eth", "erc20", "rpc", "log", "block"],
    "sui": ["sui", "move", "checkpoint", "walrus"],
    "data-platform": ["data platform", "etl", "bi", "pipeline"],
    "frontend": ["react", "next.js", "tailwind", "css", "ui"],
    "backend": ["api", "backend", "auth", "service"],
    "python": ["python", "asyncio", "multiprocessing"]
}


def sanitize_filename(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", name).strip()[:120]


def extract_messages(mapping: dict):
    messages = []

    for node in mapping.values():
        msg = node.get("message")
        if not msg:
            continue

        role = msg.get("author", {}).get("role")
        content = msg.get("content", {})
        parts = content.get("parts", [])

        texts = []

        for part in parts:
            # ✅ 普通字符串
            if isinstance(part, str):
                texts.append(part)

            # ✅ 富文本结构（最常见）
            elif isinstance(part, dict):
                # 优先取 text 字段
                if "text" in part and isinstance(part["text"], str):
                    texts.append(part["text"])

                # 有些是 content/text
                elif "content" in part and isinstance(part["content"], str):
                    texts.append(part["content"])

                # 其他类型（tool_call / image / attachment）直接忽略

        if role and texts:
            full_text = "\n".join(texts).strip()
            if full_text:
                messages.append((role, full_text))

    return messages



def classify_topics(title: str, messages):
    text = title.lower()
    for _, msg in messages:
        text += "\n" + msg.lower()

    matched = set()
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                matched.add(topic)
                break

    return matched or {"uncategorized"}

def export_conversation(conv: dict, index_registry: dict):
    if "mapping" not in conv:
        return

    title = conv.get("title") or "Untitled"
    conv_id = conv.get("id")
    ts = conv.get("create_time", 0)

    dt = datetime.fromtimestamp(ts)
    year = str(dt.year)
    month = f"{dt.month:02d}"

    messages = extract_messages(conv.get("mapping", {}))
    if not messages:
        return

    main_topic, secondary_topics = classify_topics_with_score(title, messages)

    out_dir = Path(OUTPUT_DIR) / year / month / main_topic
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = sanitize_filename(title) + ".md"
    out_path = out_dir / filename

    # ---------- 写 Markdown ----------
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f"title: {title}\n")
        f.write(f"date: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"main_topic: {main_topic}\n")
        f.write(f"tags: [{', '.join([main_topic] + secondary_topics)}]\n")
        f.write(f"conversation_id: {conv_id}\n")
        f.write("---\n\n")

        for role, text in messages:
            if role == "user":
                f.write("## 🧑 User\n")
            elif role == "assistant":
                f.write("## 🤖 Assistant\n")
            else:
                f.write(f"## {role}\n")

            f.write(text)
            f.write("\n\n")

    # ---------- 注册到 INDEX ----------
    index_registry.setdefault((year, month, main_topic), []).append(filename)

    print(f"✔ [{main_topic}] {out_path}")






def classify_topics_with_score(title: str, messages):
    text = title.lower()
    for _, msg in messages:
        text += "\n" + msg.lower()

    scores = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = 0
        for kw in keywords:
            score += text.count(kw)
        if score > 0:
            scores[topic] = score

    if not scores:
        return "uncategorized", []

    # 主主题 = 命中最高
    main_topic = max(scores, key=scores.get)

    # 次主题 = 其他
    secondary = [t for t in scores.keys() if t != main_topic]

    return main_topic, secondary


def write_indexes(index_registry):
    for (year, month, topic), files in index_registry.items():
        index_path = Path(OUTPUT_DIR) / year / month / topic / "INDEX.md"

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(f"# {topic.upper()} — {year}-{month}\n\n")
            for name in sorted(files):
                f.write(f"- [{name.replace('.md', '')}]({name})\n")

        print(f"📌 INDEX generated: {index_path}")



def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        conversations = data
    else:
        conversations = data.get("conversations", [])

    print(f"Found {len(conversations)} conversations")

    index_registry = {}

    for conv in conversations:
        export_conversation(conv, index_registry)

    write_indexes(index_registry)

    print("🎉 Export completed with MAIN topic + INDEX.md")




if __name__ == "__main__":
    main()
