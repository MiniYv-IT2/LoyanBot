"""费用计算 — 基于 LiteLLM 模型计价表"""

try:
    from litellm import model_cost as _litellm_cost
except Exception:
    _litellm_cost = {}


def calculate(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    key = f"{provider}/{model}" if "/" in model else model
    info = _litellm_cost.get(key) or _litellm_cost.get(model)

    if not info:
        for k, v in _litellm_cost.items():
            if model in k or key in k:
                info = v
                break

    if not info:
        return 0.0

    inp = (info.get("input_cost_per_token") or 0) * prompt_tokens
    out = (info.get("output_cost_per_token") or 0) * completion_tokens
    return round(inp + out, 6)
