# StudyDeck

StudyDeck 是一个**主题专属的中文学习卡片复习 CLI**：用正面问题/背面答案组织知识，按标签筛选到期卡片，记录 0–5 熟练度评分，并用简明间隔重复算法安排下一次复习与估算难度。

## 功能边界

- 支持本地 JSON 文件、正反面文本、逗号分隔标签、到期查询、评分和统计。
- 算法是易读的启发式 SRS，不是 Anki/SM-2 的兼容实现；不提供云同步、账号、多用户、图片/音频或加密。
- 日期使用运行机器的本地日历日期；同一天重复评分会覆盖当前卡片状态并增加复习次数。

## 要求与安装

需要 **Python 3.10 或更高版本**，仅运行时使用 Python 标准库。开发安装：

```bash
python -m pip install -e .
```

默认数据文件为 `~/.studydeck.json`。建议测试时显式指定临时路径：`--data ./my-cards.json`（`--db` 是同义参数），或设置 `STUDYDECK_DATA` 环境变量。写入采用同目录临时文件、fsync 后原子替换。

## CLI 完整示例

```bash
studydeck --data ./deck.json add "TCP 三次握手" "SYN、SYN-ACK、ACK" --tags 网络,协议
studydeck --data ./deck.json add "列表推导式" "[f(x) for x in xs]" --id py --tags Python
studydeck --data ./deck.json list
studydeck --data ./deck.json list --due
studydeck --data ./deck.json list --tag 网络 --due
studydeck --data ./deck.json review 1 5
studydeck --data ./deck.json stats
```

示例输出：

```text
已创建卡片 1（今日到期）
1 张卡片：
1 | TCP 三次握手 -> SYN、SYN-ACK、ACK | 标签：协议,网络 | 到期：2025-01-01 | 难度：0.50
已记录 1：评分 5，下次复习 2025-01-04（间隔 3 天，难度 0.42）
卡片总数：1
今日到期：0
复习次数：1
最近评分均值：5.00
```

## 命令与参数

全局参数必须放在子命令前：`--data PATH` / `--db PATH` 指定 JSON 文件。

- `add FRONT BACK [--id ID] [--tags TAG1,TAG2]`：创建卡片；省略 ID 自动使用下一个数字 ID，创建时立即到期。
- `list [--tag TAG] [--due]`（别名 `cards`）：列出全部、按标签或只列出日期不晚于今天的卡片。
- `review ID RATING`：`RATING` 必须为 0–5 整数；记录评分并更新间隔、难度和下次日期。
- `stats`：显示卡片总数、今日到期数、复习总次数和所有已复习卡片“最近一次评分”的算术平均值（不是全部历史评分均值）。
- `--help`：查看帮助。

间隔规则：0–2 分重置为 1 天并提高难度；3 分乘 1.4；4 分乘 2.2；5 分乘 3.0；首次复习分别从 1/2/3 天起。难度是 0–1 的可解释估计值。

## 数据格式、隐私与安全

JSON 顶层包含 `version` 和 `cards` 对象；卡片字段包括 `front`、`back`、`tags`、`created`、`due`、`interval`、`difficulty`、`reviews`、`last_rating`，复习后还会有 `last_review`。`examples/sample.json` 是无个人数据示例。数据只写入你指定的本地路径；本程序不联网、不上传、不读取凭据。请自行设置文件权限并备份；程序不提供加密，敏感内容不应放入卡片。程序读取时会校验卡片字段类型、日期、间隔、难度和评分范围；损坏或结构异常的 JSON 会报错而不会覆盖原文件。

## 开发与测试

```bash
python -m unittest discover -s tests -v
```

测试全部使用 `tempfile.TemporaryDirectory`，不会接触真实用户数据。CI 在 Python 3.10 上执行安装和 unittest。

## 许可证

MIT License，见 `LICENSE`。
