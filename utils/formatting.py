import math
from datetime import datetime, timedelta

def format_size(size):
    if size == 0: return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s:g} {size_names[i]}"

def format_date(timestamp):
    dt = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    if dt.date() == now.date():
        return f"Today at {dt.strftime('%H:%M')}"
    elif dt.date() == (now - timedelta(days=1)).date():
        return f"Yesterday at {dt.strftime('%H:%M')}"
    else:
        return dt.strftime('%d %b %Y %H:%M')
