# 当前交付状态

## 角色

| MOD id | 角色 | 版本 | 发布目录 | 构建目录 |
|---|---|---|---|---|
| `zzz_Nte_Zero_P` | 零 | 1.0.2 | `Release/Mods/zzz_Nte_Zero_P/` | `Builds/zero/current` |
| `zzz_Nte_Mint_P` | 薄荷 | 制作中 | `Release/Mods/zzz_Nte_Mint_P/` | `Builds/mint/current` |

同一时间只能安装一个角色 MOD：两者共用主角槽位。仓库与发行名统一为 `PhantomBladeZero-NTE-Character-Mod`，角色差异只在 profile（`Pipeline/native-zero/mods/<profile>.json`）。

## 零 1.0.2

- 骨架：`Hun_Skin_Skeleton`，264 骨，根 `root`
- cooked 网格：59,851 顶点、82,945 三角、180.627 cm，最多 4 影响
- 模型：`Builds/zero/current/zero_clean.blend`、`zero_clean.fbx`
- 容器：`zzz_Nte_Zero_P.{pak,utoc,ucas}`，pak 504B、utoc 17,231B、ucas 68,369,712B

1.0.2 只做命名整改：MOD id 由 `zzz_NteZeroNative_P` 改为 `zzz_Nte_Zero_P`，容器与资产内容不变。改名会改变容器文件名与包内 marker 文本，因此用新版本号重新打包，避免同版本不同二进制。

### 1.0.2 内容等价证明

旧容器（`Builds/zero/v1.0.1/container`）与新容器逐字节比对：

- `.ucas` 长度相同，68,369,712 字节中仅 8 字节不同（offset 68,368,152）。
- `.utoc` 长度相同，1,661 字节不同，集中在 36 段 8–16 字节的哈希簇。
- `.pak` 503 → 504 字节，差异为 marker 文本 `zzz_Nte_Zero_P 1.0.2`。

资产级证明：用 `SkelDump save` 从两个容器分别导出全部 46 个文件（42 个资产 + 3 个 `.ubulk` + marker），比对 SHA-256，45 个完全一致，唯一差异是 marker 文本。报告存在 `Builds/zero/current/container_equivalence.json`。

### 1.0.1 改动（内容基线）

- 颈部：`neck_02` 与 `head` 的平移比例由 0.8 回到 1.0，颈段长度恢复原生比例，头部随之上移 1.80 cm、身高 178.828 → 180.627 cm；颈部柱面 896 个顶点重新分配权重（此前 `neck_02` 无任何权重，上颈 91% 刚性跟随头骨）。
- 手指：10 根手指链的皮肤沿各自 `01 → 03` 骨轴缩短 5%，指尖投影 10.117 → 9.610 cm（中指），骨骼、权重与 UV 未变。

## 验证结果（零）

- 资产 QA：`Builds/zero/current/source_asset_qa.json`
- 骨架与 refpose：`Builds/zero/current/refpose_validation.json`
- 颈部与手指改动量：`Builds/zero/current/neck_finger_refinement.json`
- 颈部与手指范围校验：`Builds/zero/current/neck_deformation_validation.json`
- 变形检查：`Builds/zero/current/review/cooked_skin_review.json`
- 握持边沿检查：`Builds/zero/current/grip_audit/grip_edge_audit.json`
- 容器内容等价：`Builds/zero/current/container_equivalence.json`
- 安装指纹：`Builds/zero/current/installed_verification.json`

安装包、仓库包与已安装三件套 SHA-256 已核对一致（`verify_installation.py` 通过）。每次更新通过 PBZModKit 管理。

## 发布渠道

- GitHub 仓库：<https://github.com/graydovee/PhantomBladeZero-NTE-Character-Mod>，tag 按角色分前缀（`zero-v*`、`mint-v*`）。1.0.0/1.0.1 的历史 tag 保留原名。
- Nexus：[mod 948](https://www.nexusmods.com/phantombladezero/mods/948)，页面文案见 [nexus-mod-page.md](nexus-mod-page.md)。
- 发行包命名：`<MOD id>-v<版本>.zip`（纯资产）、`PhantomBladeZero-NTE-Character-Mod-<MOD id>-v<版本>.zip`（安装器 + 全部角色包）、`PhantomBladeZero-NTE-Character-Mod-Nexus-<MOD id>-v<版本>.zip`（Nexus 单角色包）。

## 薄荷（制作中）

- 源模型：Sketchfab Mint Swimsuit Animated（作者 Jun Hungry，CC BY 4.0），101.4k 三角 / 53.5k 顶点，尚未下载。
- 复用零已验证的材质路线：同一 `MI_ZeroHun_Cap_01_b` 与 `T_ZeroHun_Cap_V02_{BC,N,ARM}` 路径，只替换贴图内容。
