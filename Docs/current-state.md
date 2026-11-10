# 当前交付状态

- MOD：`zzz_NteZeroNative_P`
- 发布版本：`1.0.1`
- 发布目录：`Release/Mods/zzz_NteZeroNative_P/`
- 工作工程：`Pipeline/native-zero/unreal/ProjectPBZ/`
- 模型：`Builds/current/zero_clean.blend`、`zero_clean.fbx`
- 骨架：`Hun_Skin_Skeleton`，264 骨，根 `root`
- cooked 网格：59,851 顶点、82,945 三角、180.627 cm，最多 4 影响

1.0.1 为正式版。用户已实机确认模型、材质、基本动画，以及本版的颈部与指尖效果。完整战斗动作、武器握持和长时间稳定性未逐项验收，实机发现问题按 1.0.x 继续迭代。

## 1.0.1 改动

- 颈部：`neck_02` 与 `head` 的平移比例由 0.8 回到 1.0，颈段长度恢复原生比例，头部随之上移 1.80 cm、身高 178.828 → 180.627 cm；颈部柱面 896 个顶点重新分配权重（此前 `neck_02` 无任何权重，上颈 91% 刚性跟随头骨）。
- 手指：10 根手指链的皮肤沿各自 `01 → 03` 骨轴缩短 5%，指尖投影 10.117 → 9.610 cm（中指），骨骼、权重与 UV 未变。

## 验证结果

- 资产 QA：`Builds/current/source_asset_qa.json`
- 骨架与 refpose：`Builds/current/refpose_validation.json`
- 颈部与手指改动量：`Builds/current/neck_finger_refinement.json`
- 颈部与手指范围校验：`Builds/current/neck_deformation_validation.json`
- 变形检查：`Builds/current/review/cooked_skin_review.json`
- 握持边沿检查：`Builds/current/grip_audit/grip_edge_audit.json`
- 安装指纹：`Builds/current/installed_verification.json`

安装包、仓库包与已安装三件套 SHA-256 已核对一致。每次更新通过 PBZModKit 管理。
