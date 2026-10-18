"""MOSS-Transcribe-Diarize as a post-hoc engine: one pass over the whole
recording gives timestamped, speaker-labelled, punctuated turns. Runs inside
src/venv-granite (transformers 5.x, the OpenMOSS package, Triton, and on a
Turing GPU the flash-attention-turing extension). The audio service invokes
this as a subprocess and reads JSON, like nemotron_cli.py / diarizen_cli.py.

Usage:
    venv-granite/bin/python moss_cli.py input.wav --out turns.json
        [--hotwords "Viking, Pat, Sandy"] [--max-new-tokens 40000] [--no-graph]

Output JSON: {"turns": [{"start": s, "end": e, "speaker": "S01", "text": "..."}, ...],
              "generated_tokens": n, "prefill_s": .., "run_s": .., "tokens_per_s": ..}
Progress for long passes: <out>.progress (tokens, audio position, head/tail).

The decode loop is our own (2026-10-18, see README "MOSS end to end"): the
model in bf16 (Qwen3's MLP overflows fp16 on an hour of audio), the Turing
flash kernel for the encoder and prefill, a pre-allocated fp16 KV cache, a
Triton split-key kernel for the single-query step, the whole step replayed as
a CUDA graph, and the vocabulary projection in fp32 so near-ties are decided
by the model rather than by bf16 rounding. On the Quadro RTX 8000 that is
about 42 tokens/s, an hour of audio in 16 minutes; HF generate managed 2-3.
On an Ampere-or-newer GPU the same loop runs with PyTorch's own kernels when
the Turing port is absent (sdpa attention, the grouped-matmul decode).
"""
import argparse
import json
import os
import sys
import time
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # HERE: the siblings below, as a script or a worker
os.environ.setdefault("HF_HUB_OFFLINE", "1")

MODEL = "OpenMOSS-Team/MOSS-Transcribe-Diarize"
PROMPT = ("Transcribe the audio. For each segment, start with the timestamp and speaker ID ([S01], [S02], [S03], ...), "
          "then the spoken text, and end with the segment timestamp.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--out", required=True)
    ap.add_argument("--hotwords", default="", help="comma-separated words the recognizer should expect (case vocabulary, names)")
    ap.add_argument("--max-new-tokens", type=int, default=40000, help="the cache is sized for this at launch; about 10 tokens per audio second")
    ap.add_argument("--no-graph", dest="graph", action="store_false", default=True)
    a = ap.parse_args()
    if not os.path.isfile(a.audio):
        sys.exit("moss_cli: no such audio file: {0}".format(a.audio))
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, cache_utils
    from moss_transcribe_diarize import parse_transcript
    from moss_transcribe_diarize.inference_utils import build_transcription_messages, process_audio_info, resolve_device
    from triton_decode import DecodeAttention
    import flash_turing_attn

    device = resolve_device("auto")
    if device.type != "cuda":
        sys.exit("moss_cli: a CUDA GPU is required")
    dtype = torch.bfloat16
    t0 = time.time()
    attn = flash_turing_attn.register()
    model = AutoModelForCausalLM.from_pretrained(MODEL, trust_remote_code=True, dtype="auto", attn_implementation=attn).to(dtype=dtype).to(device).eval()
    processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True)
    load_s = time.time() - t0
    prompt = PROMPT + (" Hotwords: " + a.hotwords if a.hotwords.strip() else "")
    with wave.open(a.audio) as w:
        audio_s = w.getnframes() / w.getframerate()

    class Store:
        cap = 0; pos = None; n_keys = None; prefill = True

    class PreallocLayer(cache_utils.DynamicLayer):
        def lazy_initialization(self, key_states, value_states):
            b, hk, _, d = key_states.shape
            self.dtype, self.device = torch.float16, key_states.device
            self.kbuf = torch.zeros(b, hk, Store.cap, d, dtype=torch.float16, device=key_states.device)
            self.vbuf = torch.zeros_like(self.kbuf)
            self.n = 0
            self.keys, self.values = self.kbuf[:, :, :0], self.vbuf[:, :, :0]
            self.is_initialized = True

        def update(self, key_states, value_states, *args, **kwargs):
            if not self.is_initialized:
                self.lazy_initialization(key_states, value_states)
            k, v = key_states.to(torch.float16), value_states.to(torch.float16)
            n = k.shape[-2]
            if Store.prefill:
                self.kbuf[:, :, self.n:self.n + n].copy_(k); self.vbuf[:, :, self.n:self.n + n].copy_(v)
                self.n += n
                self.keys, self.values = self.kbuf[:, :, :self.n], self.vbuf[:, :, :self.n]
                return self.keys, self.values
            self.kbuf.index_copy_(2, Store.pos, k); self.vbuf.index_copy_(2, Store.pos, v)
            self.n += 1
            self.keys, self.values = self.kbuf[:, :, :self.n], self.vbuf[:, :, :self.n]
            return self.kbuf, self.vbuf

    # ---- prefill through the model's own forward (audio features -> language model) ----
    t0 = time.time()
    messages = build_transcription_messages(a.audio, prompt=prompt)
    text_in = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    audios = process_audio_info(messages, sampling_rate=processor.feature_extractor.sampling_rate)
    inputs = processor(text=[text_in], audio=audios, max_length=131072, audio_kwargs={"device": str(device)}, return_tensors="pt").to(device)
    prompt_len = int(inputs["attention_mask"][0].sum().item())
    Store.cap = prompt_len + a.max_new_tokens + 8
    Store.prefill = True
    cache = cache_utils.DynamicCache()
    tc = model.config.text_config
    cache.layers = [PreallocLayer() for _ in range(tc.num_hidden_layers)]
    dec = DecodeAttention(1, tc.num_attention_heads, tc.num_key_value_heads, tc.head_dim, Store.cap, device)
    head_w = model.lm_head.weight.float()

    def project(hidden):
        return torch.matmul(hidden.float(), head_w.t())

    with torch.inference_mode(), torch.amp.autocast("cuda", dtype=dtype):
        out = model.model(input_ids=inputs["input_ids"], attention_mask=None, input_features=inputs["input_features"],
                          audio_feature_lengths=inputs["audio_feature_lengths"], audio_chunk_mapping=inputs["audio_chunk_mapping"],
                          past_key_values=cache, use_cache=True)
        tok = project(out.last_hidden_state[:, -1]).argmax(-1)
    torch.cuda.synchronize()
    prefill_s = time.time() - t0
    del out

    # ---- decode loop ----
    Store.prefill = False
    Store.pos = torch.full((1,), prompt_len, dtype=torch.long, device=device)
    Store.n_keys = torch.full((1,), prompt_len + 1, dtype=torch.int32, device=device)

    class _D:
        pass
    flash_turing_attn.DECODE = _D(); flash_turing_attn.DECODE.att = dec; flash_turing_attn.DECODE.n_keys = Store.n_keys
    lm = model.model.language_model
    eos = model.generation_config.eos_token_id
    eos = set(eos if isinstance(eos, (list, tuple)) else [eos])
    pos_ids = Store.pos.view(1, 1)

    def step(tok_in):
        h = lm.embed_tokens(tok_in.view(1, 1))
        o = lm(inputs_embeds=h, position_ids=pos_ids, cache_position=Store.pos, past_key_values=cache, use_cache=True)
        nxt = project(o.last_hidden_state[:, -1]).argmax(-1)
        Store.pos.add_(1); Store.n_keys.add_(1)
        return nxt

    generated = []
    t0 = time.time(); last_report = 0; graph = None; static_in = static_out = None

    def report():
        text = processor.tokenizer.decode(generated, skip_special_tokens=True)
        segs = parse_transcript(text)
        reached = float(segs[-1].end) if segs else 0.0
        json.dump({"generated_tokens": len(generated), "audio_reached_s": round(reached, 1), "audio_s": round(audio_s, 1),
                   "pct": round(100 * reached / max(audio_s, 1e-9), 1), "elapsed_s": round(time.time() - t0, 1),
                   "tok_per_s": round(len(generated) / max(time.time() - t0, 1e-9), 2), "segments": len(segs),
                   "head": text[:160], "tail": text[-160:]}, open(a.out + ".progress", "w"))

    with torch.inference_mode(), torch.amp.autocast("cuda", dtype=dtype):
        n = 0
        while n < a.max_new_tokens:
            t = int(tok.item())
            if t in eos:
                break
            generated.append(t)
            if a.graph and n == 3 and graph is None:
                static_in = tok.clone()
                s = torch.cuda.Stream(); s.wait_stream(torch.cuda.current_stream())
                graph = torch.cuda.CUDAGraph()
                with torch.cuda.graph(graph, stream=s):
                    static_out = step(static_in)
                torch.cuda.current_stream().wait_stream(s)
            if graph is not None:
                static_in.copy_(tok); graph.replay(); tok = static_out
            else:
                tok = step(tok)
            n += 1
            if n - last_report >= (100 if n < 1000 else 250):
                last_report = n; report()
    run_s = time.time() - t0
    text = processor.tokenizer.decode(generated, skip_special_tokens=True).strip()
    turns = [{"start": round(float(sg.start), 3), "end": round(float(sg.end), 3), "speaker": str(sg.speaker), "text": (sg.text or "").strip()}
             for sg in parse_transcript(text)]
    turns.sort(key=lambda t: (t["start"], t["end"]))
    with open(a.out, "w") as f:
        json.dump({"model": MODEL, "attention": attn, "turns": turns, "generated_tokens": len(generated), "audio_s": round(audio_s, 1),
                   "load_s": round(load_s, 1), "prefill_s": round(prefill_s, 1), "run_s": round(run_s, 1),
                   "tokens_per_s": round(len(generated) / max(run_s, 1e-9), 1), "capped": n >= a.max_new_tokens,
                   "gpu_peak_mib": int(torch.cuda.max_memory_allocated() // 2**20)}, f)
    try:
        os.remove(a.out + ".progress")
    except OSError:
        pass
    print("wrote {0} turns, {1} speakers, {2} tokens in {3:.0f}s ({4:.1f} tok/s), prefill {5:.0f}s".format(
        len(turns), len({t["speaker"] for t in turns}), len(generated), run_s, len(generated) / max(run_s, 1e-9), prefill_s))


if __name__ == "__main__":
    main()
