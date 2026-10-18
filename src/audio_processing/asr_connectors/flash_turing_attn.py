"""transformers attention backend "turing_fa": FlashAttention-2 for Turing
(sm75) from ssiu/flash-attention-turing, which PyTorch's own flash kernel does
not cover (it needs sm80+). Register once, then load a model with
attn_implementation="turing_fa".

The port supports fp16, head dims 64/96/128, causal and grouped-query
attention, but no padding mask, dropout or KV-cache kernel. So: the mask
function registered here is the flash one (None when nothing is padded), a
single-query step (decode) runs non-causal against the whole cache, and
anything the kernel cannot take falls back to SDPA for that call.
"""
import os
import sys
import torch
from transformers.integrations.sdpa_attention import sdpa_attention_forward

# The port installs only its CUDA extension (flash_attn_turing); the Python
# wrapper stays in the checkout, so that directory is put on the path.
PORT_DIR = os.environ.get("FLASH_ATTENTION_TURING_DIR",
                          os.path.join(os.path.expanduser("~"), "src", "flash-attention-turing"))
try:
    from flash_attention_interface import flash_attn_func
except ImportError:
    sys.path.insert(0, PORT_DIR)
    from flash_attention_interface import flash_attn_func

HEAD_DIMS = (64, 96, 128)
DECODE_CHUNK = 4096
STATS = {"flash": 0, "fallback": 0}
# Set by moss_fast.py when its pre-allocated cache is in use: the single-query
# step then runs the Triton split-key kernel over the full-capacity cache with
# the valid length read from DECODE.n_keys on the device (CUDA-graph safe).
DECODE = None


def decode_attention(query, key, value, scaling=None):
    """One query per head against the whole cache (the decode step): a grouped
    matmul that reads the 8 key/value heads once, no expansion to 16 heads,
    softmax in fp32. Flash and SDPA kernels parallelise over query blocks and
    idle the GPU for a single query (13-18 ms per layer at 64K keys here);
    this runs near memory bandwidth."""
    b, h, _, d = query.shape
    hk, L = key.shape[1], key.shape[2]
    g = h // hk
    q = query.reshape(b, hk, g, d)                                         # (b, hk, group, d)
    scores = torch.matmul(q, key.transpose(-1, -2)).float() * (scaling if scaling is not None else d ** -0.5)
    probs = torch.softmax(scores, dim=-1).to(value.dtype)                  # (b, hk, group, L)
    # probs @ value as one GEMM with K = L is cuBLAS's worst shape here (3.3 ms
    # at 49K keys); the same product over 4K-key chunks summed afterwards runs
    # in 0.9 ms. The tail shorter than a chunk is one small GEMM.
    C = DECODE_CHUNK
    n = L // C
    out = None
    if n:
        Lm = n * C
        pc = probs[..., :Lm].reshape(b, hk, g, n, C).transpose(2, 3)        # (b, hk, n, group, C)
        vc = value[:, :, :Lm, :].reshape(b, hk, n, C, d)                    # (b, hk, n, C, d)
        out = torch.matmul(pc, vc).float().sum(2)                           # (b, hk, group, d)
    if L % C:
        tail = torch.matmul(probs[..., n * C:], value[:, :, n * C:, :]).float()
        out = tail if out is None else out + tail
    return out.to(value.dtype).reshape(b, h, 1, d).transpose(1, 2)         # (b, 1, h, d)


def turing_fa_attention_forward(module, query, key, value, attention_mask, dropout=0.0, scaling=None,
                                   is_causal=None, **kwargs):
    # query/key/value arrive as (batch, heads, seq, dim); return (batch, seq, heads, dim).
    q_len, dim = query.shape[2], query.shape[3]
    causal = is_causal if is_causal is not None else getattr(module, "is_causal", False)
    usable = (dim in HEAD_DIMS and query.dtype in (torch.float16, torch.bfloat16)
              and key.dtype in (torch.float16, torch.bfloat16) and value.dtype == key.dtype
              and attention_mask is None and not dropout and query.shape[1] % key.shape[1] == 0)
    if not usable:
        STATS["fallback"] += 1
        return sdpa_attention_forward(module, query, key, value, attention_mask, dropout=dropout, scaling=scaling,
                                      is_causal=is_causal, **kwargs)
    # The kernel is fp16-only. A bf16 model (the safe dtype for Qwen3's MLP and
    # residual stream, which overflow fp16 on long inputs) runs only its
    # attention core here in fp16; q and k are per-head normalised in Qwen3,
    # and the clamp guards the rare value that would not fit.
    out_dtype = query.dtype
    if out_dtype != torch.float16:
        # k/v are already fp16 when the cache patch below is active (one cast
        # at insert time instead of a cache-sized cast on every decode step).
        query = query.to(torch.float16)
        if key.dtype != torch.float16:
            key, value = key.to(torch.float16), value.to(torch.float16)
    if q_len == 1:
        STATS["decode"] = STATS.get("decode", 0) + 1
        if DECODE is not None:
            out = DECODE.att(query.squeeze(2), key, value, DECODE.n_keys, scaling if scaling is not None else dim ** -0.5)
            return out.unsqueeze(1).to(out_dtype), None
        return decode_attention(query, key, value, scaling).to(out_dtype), None
    STATS["flash"] += 1
    q = query.transpose(1, 2).contiguous()
    k = key.transpose(1, 2).contiguous()
    v = value.transpose(1, 2).contiguous()
    out = flash_attn_func(q, k, v, scaling, bool(causal))
    return out.to(out_dtype), None


def patch_cache_fp16():
    """Keep the generation KV cache in fp16 whatever the model's dtype: the
    kernel reads fp16, and casting a bf16 cache on every decode step cost
    about a gigabyte of traffic per layer per token at 44K keys."""
    from transformers import cache_utils
    layer = cache_utils.DynamicLayer
    if getattr(layer, "_turing_fp16", False):
        return
    orig_init, orig_update = layer.lazy_initialization, layer.update

    def lazy_initialization(self, key_states, value_states):
        return orig_init(self, key_states.to(torch.float16), value_states.to(torch.float16))

    def update(self, key_states, value_states, cache_kwargs=None):
        return orig_update(self, key_states.to(torch.float16), value_states.to(torch.float16), cache_kwargs)

    layer.lazy_initialization, layer.update, layer._turing_fp16 = lazy_initialization, update, True


def register(fp16_cache=True):
    from transformers.modeling_utils import ALL_ATTENTION_FUNCTIONS
    from transformers.masking_utils import ALL_MASK_ATTENTION_FUNCTIONS, flash_attention_mask
    ALL_ATTENTION_FUNCTIONS.register("turing_fa", turing_fa_attention_forward)
    ALL_MASK_ATTENTION_FUNCTIONS.register("turing_fa", flash_attention_mask)
    if fp16_cache:
        patch_cache_fp16()
    return "turing_fa"
