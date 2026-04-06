from prometheus_client import Counter, Gauge, Histogram

commands_total = Counter(
    "centpai_commands_total",
    "Total number of telegram commands processed",
    ["command"] 
)

active_members_gauge = Gauge(
    "centpai_active_members_total",
    "Total active members across all chats"
)

active_chats_gauge = Gauge(
    "centpai_active_chats_total",
    "Number of chats using the bot"
)

command_duration_seconds = Histogram(
    "centpai_command_duration_seconds",
    "Time spent processing telegram commands",
    ["command"]
)