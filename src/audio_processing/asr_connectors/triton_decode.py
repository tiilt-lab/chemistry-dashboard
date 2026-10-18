"""Split-key decode attention for Turing in Triton: one query per head against a
long, pre-allocated fp16 KV cache, grouped-query aware (the g query heads that
share a KV head are handled by the same program so K/V are read once), with an
online softmax per key slice and a combine step over the slices. The number of
valid keys is read from a device tensor, so a CUDA graph that captured the
launch stays correct as the cache grows. fp32 accumulation; no tl.dot (Turing
needs M>=16 for it and a decode step has 1-2 queries per KV head), so the dot
products are broadcast multiply-adds, which is fine for a bandwidth-bound step.
"""
import torch
import triton
import triton.language as tl


@triton.jit
def decode_split_kernel(Q, K, V, LEN, M_OUT, L_OUT, ACC_OUT, sm_scale, HK,
                        stride_qb, stride_qh, stride_kb, stride_kh, stride_kn,
                        stride_vb, stride_vh, stride_vn,
                        stride_mb, stride_mh, stride_ms, stride_ab, stride_ah, stride_as, stride_ag,
                        KEYS_PER_SPLIT: tl.constexpr, BLOCK_N: tl.constexpr, G: tl.constexpr, D: tl.constexpr, ROUND16: tl.constexpr):
    bh = tl.program_id(0)
    split = tl.program_id(1)
    b = bh // HK
    hk = bh % HK
    n_keys = tl.load(LEN + b)                      # valid keys for this batch row (int32)
    start = split * KEYS_PER_SPLIT
    end = tl.minimum(start + KEYS_PER_SPLIT, n_keys)
    offs_g = tl.arange(0, G)
    offs_d = tl.arange(0, D)
    # q: (G, D) — the G query heads that share this kv head are hk*G .. hk*G+G-1
    q_ptrs = Q + b * stride_qb + (hk * G + offs_g)[:, None] * stride_qh + offs_d[None, :]
    q = tl.load(q_ptrs).to(tl.float32) * sm_scale
    m_i = tl.full((G,), float("-inf"), tl.float32)
    l_i = tl.zeros((G,), tl.float32)
    acc = tl.zeros((G, D), tl.float32)
    k_base = K + b * stride_kb + hk * stride_kh
    v_base = V + b * stride_vb + hk * stride_vh
    for n0 in range(start, end, BLOCK_N):
        offs_n = n0 + tl.arange(0, BLOCK_N)
        mask_n = offs_n < end
        k = tl.load(k_base + offs_n[:, None] * stride_kn + offs_d[None, :], mask=mask_n[:, None], other=0.0).to(tl.float32)
        s = tl.sum(q[:, None, :] * k[None, :, :], axis=2)             # (G, BLOCK_N)
        if ROUND16:   # mimic the fp16 matmul path: scores leave the GEMM as fp16
            s = (s / sm_scale).to(tl.float16).to(tl.float32) * sm_scale
        s = tl.where(mask_n[None, :], s, float("-inf"))
        m_new = tl.maximum(m_i, tl.max(s, axis=1))
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(s - m_new[:, None])
        if ROUND16:   # and the probabilities are fp16 before the value product
            p = p.to(tl.float16).to(tl.float32)
        l_i = l_i * alpha + tl.sum(p, axis=1)
        v = tl.load(v_base + offs_n[:, None] * stride_vn + offs_d[None, :], mask=mask_n[:, None], other=0.0).to(tl.float32)
        acc = acc * alpha[:, None] + tl.sum(p[:, :, None] * v[None, :, :], axis=1)
        m_i = m_new
    m_ptrs = M_OUT + b * stride_mb + (hk * G + offs_g) * stride_mh + split * stride_ms
    tl.store(m_ptrs, m_i)
    tl.store(L_OUT + b * stride_mb + (hk * G + offs_g) * stride_mh + split * stride_ms, l_i)
    a_ptrs = ACC_OUT + b * stride_ab + (hk * G + offs_g)[:, None] * stride_ah + split * stride_as + offs_d[None, :] * stride_ag
    tl.store(a_ptrs, acc)


class DecodeAttention:
    """Holds the split buffers for a fixed (batch, heads, capacity) so a
    captured CUDA graph can replay it; call it per layer."""

    def __init__(self, batch, n_heads, n_kv_heads, head_dim, capacity, device, n_splits=128, block_n=16, num_warps=1, round16=False):
        self.b, self.h, self.hk, self.d, self.cap = batch, n_heads, n_kv_heads, head_dim, capacity
        self.g = n_heads // n_kv_heads
        self.n_splits = n_splits
        self.block_n = block_n
        self.num_warps = num_warps
        self.round16 = round16
        self.keys_per_split = -(-capacity // n_splits)
        self.keys_per_split = -(-self.keys_per_split // block_n) * block_n     # multiple of BLOCK_N
        self.m = torch.empty(batch, n_heads, n_splits, device=device, dtype=torch.float32)
        self.l = torch.empty(batch, n_heads, n_splits, device=device, dtype=torch.float32)
        self.acc = torch.empty(batch, n_heads, n_splits, head_dim, device=device, dtype=torch.float32)

    def __call__(self, q, k, v, n_keys, sm_scale):
        """q: (b, h, d) fp16; k, v: (b, hk, cap, d) fp16 (any strides on the first
        three dims, contiguous head_dim); n_keys: (b,) int32 device tensor.
        Returns (b, h, d) in q's dtype."""
        b, h, d = q.shape
        assert d == self.d and h == self.h and k.shape[1] == self.hk
        grid = (b * self.hk, self.n_splits)
        decode_split_kernel[grid](
            q, k, v, n_keys, self.m, self.l, self.acc, sm_scale, self.hk,
            q.stride(0), q.stride(1), k.stride(0), k.stride(1), k.stride(2),
            v.stride(0), v.stride(1), v.stride(2),
            self.m.stride(0), self.m.stride(1), self.m.stride(2),
            self.acc.stride(0), self.acc.stride(1), self.acc.stride(2), self.acc.stride(3),
            KEYS_PER_SPLIT=self.keys_per_split, BLOCK_N=self.block_n, G=self.g, D=self.d, ROUND16=self.round16, num_warps=self.num_warps)
        # combine the splits (tiny tensors): weights exp(m_s - m), normalise
        m = self.m.amax(dim=2, keepdim=True)                               # (b, h, 1)
        w = torch.exp(self.m - m)                                          # (b, h, S); empty splits: exp(-inf) = 0
        l = (w * self.l).sum(dim=2)                                        # (b, h)
        out = (w.unsqueeze(-1) * self.acc).sum(dim=2) / l.unsqueeze(-1)    # (b, h, d)
        return out.to(q.dtype)
