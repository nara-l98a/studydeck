from __future__ import annotations
import argparse, json, os, sys, tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_DATA = Path.home() / ".studydeck.json"

def today() -> date: return date.today()

def load_data(path: Path) -> dict[str, Any]:
    if not path.exists(): return {"version": SCHEMA_VERSION, "cards": {}}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取数据文件：{exc}") from exc
    if not isinstance(obj, dict) or not isinstance(obj.get("cards", {}), dict):
        raise ValueError("数据文件格式无效：cards 必须是对象")
    for cid, card in obj["cards"].items():
        if not isinstance(card, dict):
            raise ValueError(f"数据文件格式无效：卡片 {cid} 必须是对象")
        for field in ("front", "back"):
            if field in card and not isinstance(card[field], str):
                raise ValueError(f"数据文件格式无效：卡片 {cid} 的 {field} 必须是文本")
        if "tags" in card and (not isinstance(card["tags"], list)
                                or not all(isinstance(tag, str) for tag in card["tags"])):
            raise ValueError(f"数据文件格式无效：卡片 {cid} 的 tags 必须是文本数组")
        if "due" in card:
            try:
                date.fromisoformat(card["due"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"数据文件格式无效：卡片 {cid} 的 due 必须是 YYYY-MM-DD 日期") from exc
        if "interval" in card and (isinstance(card["interval"], bool)
                                    or not isinstance(card["interval"], (int, float))
                                    or card["interval"] < 0):
            raise ValueError(f"数据文件格式无效：卡片 {cid} 的 interval 必须是非负数字")
        if "difficulty" in card and (isinstance(card["difficulty"], bool)
                                      or not isinstance(card["difficulty"], (int, float))
                                      or not 0 <= card["difficulty"] <= 1):
            raise ValueError(f"数据文件格式无效：卡片 {cid} 的 difficulty 必须在 0 到 1 之间")
        if "reviews" in card and (isinstance(card["reviews"], bool)
                                   or not isinstance(card["reviews"], int)
                                   or card["reviews"] < 0):
            raise ValueError(f"数据文件格式无效：卡片 {cid} 的 reviews 必须是非负整数")
        if "last_rating" in card and card["last_rating"] is not None and (
                isinstance(card["last_rating"], bool) or not isinstance(card["last_rating"], int)
                or not 0 <= card["last_rating"] <= 5):
            raise ValueError(f"数据文件格式无效：卡片 {cid} 的 last_rating 必须是 0 到 5 的整数或 null")
    return obj

def save_data(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise

def clean_tags(raw: str | None) -> list[str]:
    return sorted({x.strip() for x in (raw or "").split(",") if x.strip()})

def require_text(value: str, label: str) -> str:
    value = value.strip()
    if not value: raise ValueError(f"{label}不能为空")
    return value

def cmd_add(args, data):
    front, back = require_text(args.front, "正面"), require_text(args.back, "反面")
    cid = args.id or str(max([int(x) for x in data["cards"] if str(x).isdigit()] + [0]) + 1)
    if cid in data["cards"]: raise ValueError(f"卡片 ID 已存在：{cid}")
    data["cards"][cid] = {"front": front, "back": back, "tags": clean_tags(args.tags), "created": today().isoformat(), "due": today().isoformat(), "interval": 0, "difficulty": 0.5, "reviews": 0, "last_rating": None}
    return f"已创建卡片 {cid}（今日到期）"

def selected(data, tag=None):
    cards = data["cards"].items()
    return [(cid, c) for cid, c in cards if not tag or tag in c.get("tags", [])]

def cmd_list(args, data):
    rows = selected(data, args.tag)
    if args.due: rows = [(i,c) for i,c in rows if c.get("due", "9999-12-31") <= today().isoformat()]
    if not rows: return "没有符合条件的卡片。"
    out = [f"{len(rows)} 张卡片："]
    for cid,c in sorted(rows, key=lambda x: (x[1].get("due", ""), x[0])):
        out.append(f"{cid} | {c['front']} -> {c['back']} | 标签：{','.join(c.get('tags',[])) or '-'} | 到期：{c.get('due','未知')} | 难度：{c.get('difficulty',0.5):.2f}")
    return "\n".join(out)

def cmd_review(args, data):
    if args.id not in data["cards"]: raise ValueError(f"找不到卡片：{args.id}")
    c = data["cards"][args.id]; rating = args.rating
    old = max(0, float(c.get("interval", 0)))
    if rating <= 2:
        interval = 1; c["difficulty"] = min(1.0, float(c.get("difficulty", .5)) + .15)
    elif rating == 3:
        interval = max(1, round(old * 1.4) if old else 1); c["difficulty"] = min(1.0, float(c.get("difficulty", .5)) + .03)
    elif rating == 4:
        interval = max(2, round(old * 2.2) if old else 2); c["difficulty"] = max(0.0, float(c.get("difficulty", .5)) - .04)
    else:
        interval = max(3, round(old * 3.0) if old else 3); c["difficulty"] = max(0.0, float(c.get("difficulty", .5)) - .08)
    c.update(interval=interval, due=(today()+timedelta(days=interval)).isoformat(), reviews=int(c.get("reviews",0))+1, last_rating=rating, last_review=today().isoformat())
    return f"已记录 {args.id}：评分 {rating}，下次复习 {c['due']}（间隔 {interval} 天，难度 {c['difficulty']:.2f}）"

def cmd_stats(args, data):
    cards = list(data["cards"].values()); total=len(cards); due=sum(c.get("due", "9999") <= today().isoformat() for c in cards); reviews=sum(int(c.get("reviews",0)) for c in cards)
    latest = [c["last_rating"] for c in cards if c.get("last_rating") is not None]
    avg = sum(latest) / len(latest) if latest else 0
    return f"卡片总数：{total}\n今日到期：{due}\n复习次数：{reviews}\n最近评分均值：{avg:.2f}"

def parser():
    p=argparse.ArgumentParser(prog="studydeck", description="StudyDeck 学习卡片间隔复习 CLI")
    p.add_argument("--data", "--db", dest="data", help="JSON 数据文件路径（也可用 STUDYDECK_DATA）")
    sub=p.add_subparsers(dest="command", required=True)
    a=sub.add_parser("add", help="创建卡片"); a.add_argument("front"); a.add_argument("back"); a.add_argument("--id"); a.add_argument("--tags", help="逗号分隔标签"); a.set_defaults(fn=cmd_add)
    l=sub.add_parser("list", aliases=["cards"], help="查看卡片"); l.add_argument("--tag"); l.add_argument("--due", action="store_true", help="只看已到期"); l.set_defaults(fn=cmd_list)
    r=sub.add_parser("review", help="记录 0-5 评分并安排复习"); r.add_argument("id"); r.add_argument("rating", type=int); r.set_defaults(fn=cmd_review)
    s=sub.add_parser("stats", help="查看学习统计"); s.set_defaults(fn=cmd_stats)
    return p

def main(argv=None):
    p=parser(); args=p.parse_args(argv)
    if args.command == "review" and not 0 <= args.rating <= 5:
        print("错误：rating 必须是 0 到 5 的整数", file=sys.stderr)
        return 2
    path=Path(args.data or os.environ.get("STUDYDECK_DATA", DEFAULT_DATA)).expanduser()
    try:
        data=load_data(path); message=args.fn(args,data)
        if args.command in {"add","review"}: save_data(path,data)
        print(message); return 0
    except (ValueError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
