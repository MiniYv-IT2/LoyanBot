"""费用计算 — 基于 LiteLLM 模型计价表，统一按人民币（元）记账

litellm 计价表单位是美元/token，本模块对外全部换算成人民币元：
    cost(元) = (input×input_price + output×output_price) × EXCHANGE_RATE
EXCHANGE_RATE 按需调整（默认 7.2）。
"""

try:
    from litellm import model_cost as _litellm_cost
except Exception:
    _litellm_cost = {}

EXCHANGE_RATE = 7.2


def calculate(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """返回人民币元（litellm 美元价格 × 汇率）"""
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
    return round((inp + out) * EXCHANGE_RATE, 4)


def yuan_per_million_to_usd_per_token(price_per_million: float) -> float:
    """元/百万 token → 美元/token（注册 litellm 自定义价格用）"""
    return price_per_million / EXCHANGE_RATE / 1_000_000
