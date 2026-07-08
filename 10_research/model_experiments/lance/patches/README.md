# Lance local patches

`10_research/model_experiments/lance/lance/` is an ignored upstream clone. Keep local code changes here as patch files so the outer DataMake repository can track the intended modification.

Apply from the upstream Lance repository root:

```bash
git apply ../patches/0001-role-aware-history-vit.patch
git apply ../patches/0002-fix-commented-inference-continuation.patch
git apply ../patches/0003-full-conversation-multiturn-chat.patch
```

## Patch list

| Patch | Purpose |
|-------|---------|
| `0001-role-aware-history-vit.patch` | Adds `element_role_array` so history videos can be VIT-only while latest direct source remains the only clean VAE source. |
| `0002-fix-commented-inference-continuation.patch` | Fixes a shell continuation broken by inline comments in `inference_lance.sh`. |
| `0003-full-conversation-multiturn-chat.patch` | Adds a full-conversation multi-turn inference prototype based on `Jayce-Ping/Lance@8b002b5`, with DataMake's role-aware latest-source VAE policy. |

`0003` is an inference-only experiment. It preserves historical user/assistant text turns as conversation context and supports mixed actions, but GPU visual quality still needs to be tested.
