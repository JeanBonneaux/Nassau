"""CPU speed-ups. steer.load() applies them when running on a CPU.

- patch_deltanet(): a drop-in for transformers' reference Gated DeltaNet
  decode step that updates the recurrent state in place. Same fp32 math,
  ~14x faster at batch 32. Always applied on CPU.
- quantize(): int8 weights with per-output-channel scales; activations are
  quantized per token on the fly and multiplied as int8 x int8 (VNNI). ~6x
  faster than bf16 matmuls on a CPU without native bf16, but approximate:
  opt in with QWEN_CPU_INT8=1.
"""

import math

import torch
from transformers.models.qwen3_5 import modeling_qwen3_5 as qwen


class Int8Linear(torch.nn.Module):
    def __init__(self, linear: torch.nn.Linear):
        super().__init__()
        w = linear.weight.detach().float()
        scale = w.abs().amax(1).clamp(min=1e-8) / 127
        q = (w / scale[:, None]).round().clamp(-127, 127).to(torch.int8)
        self.register_buffer("qweight_t", q.T.contiguous())
        self.register_buffer("scale", scale)

    @property
    def weight(self) -> torch.Tensor:
        """Dequantized weight, for code that reads columns of W_down."""
        return self.qweight_t.T.float() * self.scale[:, None]

    def forward(self, x):
        x2 = x.reshape(-1, x.shape[-1]).float()
        s = x2.abs().amax(1, keepdim=True).clamp(min=1e-8) / 127
        y = torch._int_mm((x2 / s).round().to(torch.int8), self.qweight_t)
        return (y.float() * s * self.scale).to(x.dtype).reshape(*x.shape[:-1], -1)


def recurrent_gated_delta_rule(
    query, key, value, g, beta, initial_state=None, output_final_state=False,
    use_qk_l2norm_in_kernel=False, **kwargs,
):
    dtype = query.dtype
    q, k, v, beta, g = (x.transpose(1, 2).float() for x in (query, key, value, beta, g))
    if use_qk_l2norm_in_kernel:
        q, k = qwen.l2norm(q, dim=-1, eps=1e-6), qwen.l2norm(k, dim=-1, eps=1e-6)
    q = q / math.sqrt(q.shape[-1])
    B, H, T, K = k.shape
    V = v.shape[-1]
    state = v.new_zeros(B, H, K, V) if initial_state is None else initial_state.float()
    flat = state.view(B * H, K, V)
    out = v.new_empty(B, H, T, V)
    for t in range(T):
        flat.mul_(g[:, :, t].exp().reshape(B * H, 1, 1))
        k_t = k[:, :, t].reshape(B * H, 1, K)
        delta = v[:, :, t].reshape(B * H, 1, V) - torch.bmm(k_t, flat)
        flat.baddbmm_(k_t.transpose(1, 2), delta * beta[:, :, t].reshape(B * H, 1, 1))
        out[:, :, t] = torch.bmm(q[:, :, t].reshape(B * H, 1, K), flat).view(B, H, V)
    return out.transpose(1, 2).contiguous().to(dtype), state if output_final_state else None


def patch_deltanet():
    qwen.torch_recurrent_gated_delta_rule = recurrent_gated_delta_rule


def quantize(model):
    """Swap every large Linear, the LM head included, for an Int8Linear."""
    for mod in list(model.modules()):
        for name, child in list(mod.named_children()):
            if isinstance(child, torch.nn.Linear) and child.weight.numel() > 1_000_000:
                setattr(mod, name, Int8Linear(child))
    return model
