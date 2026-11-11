# PhantomBladeZero-NTE-Character-Mod — Zero 1.0.2

Zero 是《异环》角色替换计划中的第一个角色，本版本只调整命名与仓库结构，模型、材质、绑定与 1.0.1 完全一致。

## 变更

- MOD id 由 `zzz_NteZeroNative_P` 改为 `zzz_Nte_Zero_P`（仓库改为多角色 `PhantomBladeZero-NTE-Character-Mod`）。
- 重新打包容器：包内资产共 46 项，其中 45 项与 1.0.1 逐字节一致，仅 `marker.txt` 因版本号更新而不同。
- 安装/卸载命令改为 `PBZModKit-cli.exe install zzz_Nte_Zero_P`。
- 包内资产路径（`MI_ZeroHun_Cap_01_b`、`T_ZeroHun_Cap_V02_*`、`SM_ZeroHun_Cloth_V02`、`/Game/NativeZero/NativeMesh_*`）全部保持不变。

## 安装

1. 完全退出游戏。
2. 运行 `PBZModKit.exe`，安装 `zzz_Nte_Zero_P` 1.0.2（或使用命令行 `PBZModKit-cli.exe install zzz_Nte_Zero_P`）。
3. 启动游戏确认主角替换；卸载后恢复原角色。

一次只能安装一个角色 MOD。安装前请卸载 1.0.1 及更早版本（旧 id `zzz_NteZeroNative_P`）。

## 已知

- 运行时画面需玩家实机验证，仓库内的离线检查（资产 QA、cook、容器反解、变形量测、安装哈希）全部通过。
