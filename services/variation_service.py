def triangular_wave(position: float, low: float, high: float, phase: float = 0.0) -> float:
    """
    Dao động dạng tam giác:
    low -> high -> low -> high ...
    """
    x = (position + phase) % 1.0
    return low + (high - low) * (1.0 - abs(2.0 * x - 1.0))

def dynamic_sentence_count(base_count: int, step: int, spread: int = 2, phase: float = 0.2) -> int:
    """
    Số câu không cố định, dao động quanh giá trị gốc.
    """
    low = max(2, base_count - spread)
    high = base_count + spread
    value = triangular_wave(step / 8.0, low, high, phase)
    return int(round(value))

def dynamic_speech_rate(base_rate: float, step: int, spread: float = 0.18, phase: float = 0.25) -> float:
    """
    Tốc độ đọc dao động trong khoảng [base_rate - spread, base_rate + spread].
    Ví dụ: base_rate=1.0 => dao động quanh 0.82 ~ 1.18
    """
    low = max(0.65, base_rate - spread)
    high = min(1.45, base_rate + spread)
    value = triangular_wave(step / 10.0, low, high, phase)
    return round(value, 2)