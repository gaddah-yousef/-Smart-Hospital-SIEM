from collections import defaultdict, deque
from time import time


class SlidingCorrelator:
    def __init__(self):
        self.events_by_ip: dict[str, deque[tuple[float, dict]]] = defaultdict(deque)

    def add(self, event: dict) -> None:
        ip = str(event.get("source_ip", "unknown"))
        now = time()
        window = self.events_by_ip[ip]
        window.append((now, event))
        while window and now - window[0][0] > 600:
            window.popleft()

    def distinct_services(self, source_ip: str, seconds: int) -> set[str]:
        now = time()
        return {
            str(event.get("job") or event.get("service") or event.get("event_type"))
            for ts, event in self.events_by_ip.get(source_ip, [])
            if now - ts <= seconds
        }

    def outbound_baseline_ratio(self, source_ip: str, seconds: int) -> float:
        now = time()
        ratios = []
        for ts, event in self.events_by_ip.get(source_ip, []):
            if now - ts <= seconds and event.get("baseline_outbound_bytes"):
                ratios.append(float(event.get("outbound_bytes", 0)) / max(float(event["baseline_outbound_bytes"]), 1.0))
        return max(ratios or [0.0])
