from prometheus_client import Counter, Gauge, Histogram

commands_total = Counter(
    "centpai_commands_total",
    "Total number of telegram commands processed",
    ["command"] 
)

command_duration_seconds = Histogram(
    "centpai_command_duration_seconds",
    "Time spent processing telegram commands",
    ["command"]
)