import discord
from datetime import datetime, timezone


def format_currency(amount: float) -> str:
    if abs(amount) >= 1_000_000:
        return f"${amount:,.0f}"
    return f"${amount:,.2f}"


def format_percent(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def format_change(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{format_currency(value)}"


def profit_color(value: float) -> discord.Color:
    if value > 0:
        return discord.Color.green()
    elif value < 0:
        return discord.Color.red()
    return discord.Color.greyple()


def profit_emoji(value: float) -> str:
    if value > 0:
        return "📈"
    elif value < 0:
        return "📉"
    return "➡️"


def rank_emoji(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")


def format_timestamp(ts) -> str:
    if ts is None:
        return "N/A"
    if isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    elif isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            return str(ts)
    elif isinstance(ts, datetime):
        dt = ts
    else:
        return str(ts)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def truncate(text: str, max_len: int = 1024) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def build_table(headers: list[str], rows: list[list[str]], col_sep: str = " | ") -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    lines = [col_sep.join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append(col_sep.join("-" * w for w in widths))
    for row in rows:
        lines.append(col_sep.join(str(c).ljust(widths[i]) for i, c in enumerate(row)))
    return "```\n" + "\n".join(lines) + "\n```"
