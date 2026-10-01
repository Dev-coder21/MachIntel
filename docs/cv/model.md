# PatchCore Anomaly Detection Model Specification

## 1. Model Overview & Identifier

- **Model Version**: `mvtec-patchcore-metalnut-v1.0.0`
- **Feature Configuration Version**: `cv-feature-config-v1.0.0`
- **Policy Version**: `cv-policy-v1.0.0`
- **Architecture**: PatchCore-style frozen-feature memory-bank anomaly detector (Roth et al., *CVPR 2022*)
- **Target Category**: `metal_nut` (MVTec AD)

---

## 2. Pretrained Backbone & Layer Configuration

The model uses a frozen **WideResNet-50-2** convolutional neural network pretrained on ImageNet-1K (`Wide_ResNet50_2_Weights.IMAGENET1K_V1`). All weights are strictly frozen with gradient computation disabled (`requires_grad = False`).

### Intermediate Feature Extraction

Intermediate activations are extracted via forward hooks on residual stages:

| Layer | Feature Channels | Spatial Resolution ($224 \times 224$ Input) | Receptive Field |
| :--- | :---: | :---: | :--- |
| **`layer2`** | 512 | $28 \times 28$ | Mid-level local geometric & textural cues |
| **`layer3`** | 1024 | $14 \times 14$ | High-level contextual & structural features |

### Spatial Alignment & Patch Representation

1. `layer3` activations are upsampled to the spatial dimensions of `layer2` ($28 \times 28$) via bilinear interpolation:
   $$\tilde{\mathbf{F}}_{\text{layer3}} = \text{Interpolate}(\mathbf{F}_{\text{layer3}}, \text{size}=(28, 28))$$
2. Features are concatenated channel-wise:
   $$\mathbf{F}_{\text{cat}} = [\mathbf{F}_{\text{layer2}} \parallel \tilde{\mathbf{F}}_{\text{layer3}}] \in \mathbb{R}^{B \times 1536 \times 28 \times 28}$$
3. Local neighborhood aggregation is applied using an average pooling operator ($3 \times 3$ kernel, stride 1, padding 1) to incorporate local spatial context:
   $$\mathbf{F}_{\text{patch}} = \text{AvgPool}_{3\times3}(\mathbf{F}_{\text{cat}})$$
4. The feature map is reshaped into $N = 28 \times 28 = 784$ patch embedding vectors per image, each of dimension $D = 1536$.

---

## 3. Normal Memory Bank Construction

The memory bank $\mathcal{M}$ represents the distribution of normal nominal industrial parts:

- **Source Images**: All 220 images from `train/good`
- **Total Raw Patches**: $220 \times 784 = 172,480$ feature vectors
- **Deterministic Coreset Subsampling**:
  To ensure tractability and high-speed nearest-neighbor search, a deterministic subsampling ratio of $5.0\%$ is applied using PyTorch random generator with fixed seed `42`:
  $$|\mathcal{M}| = 8,624 \text{ patch vectors}$$
  $$\text{Memory Footprint} \approx 8,624 \times 1,536 \times 4 \text{ bytes} \approx 53.0 \text{ MB}$$

---

## 4. Nearest-Neighbor Inference & Anomaly Scoring

For an unseen query image $I_{\text{test}}$, patch embeddings $\mathcal{P} = \{p_1, p_2, \dots, p_{784}\} \subset \mathbb{R}^{1536}$ are extracted.

### Patch Anomaly Distance
The distance $d(p_i)$ of patch $p_i$ to the memory bank is its Euclidean distance to its nearest normal neighbor:
$$d(p_i) = \min_{m \in \mathcal{M}} \|p_i - m\|_2$$

Computed via vectorized expansion:
$$\|p_i - m\|_2^2 = \|p_i\|_2^2 + \|m\|_2^2 - 2 p_i \cdot m^T$$

### Image-Level Anomaly Score
The image-level score $s^*$ is the maximum patch distance across the spatial grid:
$$s^* = \max_{i \in \{1, \dots, 784\}} d(p_i)$$

Typical inference latency is **$\approx 38\text{ ms}$** per image on local Apple Silicon CPU.
