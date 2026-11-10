# 影之刃零 × 异环·零

工程覆盖模型适配、材质、骨骼重定向、动画驱动、IoStore 打包管线和安装器 PBZModKit。

仓库只保存源码、文档和制作 skill；角色模型、游戏原生资产与制作中间文件在本地取得，不随仓库分发。

## 下载与安装

发布包在 GitHub Release 中提供：

<https://github.com/graydovee/PhantomBladeZero-NTE-Zero-Mod/releases>

下载 `PhantomBladeZero-NTE-Zero-Mod-v1.0.1.zip` 并解压，得到 `PBZModKit.exe`、`PBZModKit-cli.exe`、`Mods/` 下的两个 MOD 包和 `使用说明.md`。

1. 完全退出游戏。
2. 运行 `PBZModKit.exe`，确认游戏目录（首次启动会自动探测 Steam 与 WeGame 的安装位置，也可以手动指定）。
3. 在列表里选中 `zzz_NteZeroNative_P` 安装；需要换回原版时在同一界面卸载。
4. 启动游戏确认角色已替换。

安装器把配置与安装记录保存在自身目录下的 `data/`，发布包不包含该目录。

需要在脚本或终端里批量操作时，使用同一目录下的命令行版本：

```powershell
& .\PBZModKit-cli.exe status
& .\PBZModKit-cli.exe install zzz_NteZeroNative_P
& .\PBZModKit-cli.exe uninstall zzz_NteZeroNative_P
```

## 准备制作环境

新克隆的仓库包含安装器源码（`App/`）、UE 工程（`Pipeline/native-zero/unreal/ProjectPBZ/`）、文档和制作 skill。要打开工程、重新烘焙并打包，在本地按顺序准备这些资产：

1. 安装依赖：Blender 4.5.15、.NET 10 SDK、UE 5.7.4，见下方「第三方依赖」。
2. 放入角色模型与贴图（Sketchfab，CC BY 4.0）。
3. 从本机《影之刃零》客户端提取游戏原生资产与原生骨架 FBX。
4. 用 `Tools/SkelDump` 导出原生骨架与网格参考数据。
5. 运行 skill 的 `make_native_blank.py` 与 `build_native_mesh.py` 生成摆姿工作文件。
6. 按 skill 第 6 步把 FBX 导入 UE 工程，在编辑器中生成工程内资产。

| 资产 | 取得方式 | 存放位置 |
|---|---|---|
| 角色模型与贴图 | Sketchfab [Esper Zero Animated - Neverness To Everness](https://sketchfab.com/3d-models/esper-zero-animated-neverness-to-everness-1ada850ff2de4d3d8a317052c2144a88)，作者 Jun Hungry，CC BY 4.0 | `Pipeline/native-zero/model/zero/character.fbx` 与 `model/zero/textures/` 下的 16 张贴图 |
| 游戏原生资产 | 本机合法《影之刃零》客户端，用 `Tools/SkelDump` 提取 | `Pipeline/native-zero/model/game/` 与 `Pipeline/native-zero/unreal/ProjectPBZ/Plugins/HuaShira/` |
| 原生骨架与网格参考数据 | 同一客户端，`SkelDump meshrich` 与 `SkelDump props` | `Pipeline/native-zero/reference/native_body_mesh.json`、`native_skeleton_props.json` |
| 摆姿工作文件 | skill 的 `make_native_blank.py` 与 `build_native_mesh.py` 生成 | `Pipeline/native-zero/source/` 下的 `SK_ZeroBody_posed.blend`、`native_blank.fbx`、`native_blank_static.fbx` |
| 原生骨架 FBX | 同一客户端提取 | `Pipeline/native-zero/blender/game/game_rig_264.fbx` |
| 工程内资产 | 导入 FBX 后在编辑器中生成 | `Pipeline/native-zero/unreal/ProjectPBZ/Content/PBZContent/` |

`model/zero/textures/` 使用这些文件名：`T_player_051_female_{1,2}_{d,n,m,id}.png`、`T_player_009_female_hair_0{1,2}_{d,m}.png`、`T_player_051_female_face_{d,m,r}.png`、`T_player_051_female_eye_d.png`。

游戏原生 PAK、AES、USMAP 同样来自本机安装，提取命令见 [workflow.md](.agents/skills/phantom-blade-zero-mod/references/workflow.md)。

## 工程结构

- 当前 UE 工程：`Pipeline/native-zero/unreal/ProjectPBZ/ProjectPBZ.uproject`
- 源模型与纹理：`Pipeline/native-zero/model/zero/`
- 原生骨架与资产参考：`Pipeline/native-zero/reference/`
- 打包白名单：`Pipeline/native-zero/tools/cook-allowlist.json`
- PBZModKit 源码：`App/`
- 当前制作 skill：`.agents/skills/phantom-blade-zero-mod/`
- 当前状态与验收要求：[Docs/current-state.md](Docs/current-state.md)、[Docs/task.md](Docs/task.md)

## 第三方依赖

| 本地路径 | 用途 | 下载或恢复位置 |
|---|---|---|
| `/Tools/blender/blender-4.5.15-windows-x64/` | Blender 4.5.15 | [Blender 4.5.15 Windows x64](https://download.blender.org/release/Blender4.5/blender-4.5.15-windows-x64.zip)，或 [Blender 官方下载页](https://www.blender.org/download/lts/4-5/) |
| `/Tools/dotnet/` | 本地 .NET SDK | [.NET 10 SDK 官方下载页](https://dotnet.microsoft.com/download/dotnet/10.0) |
| `.agents/skills/blender-*` | 通用 Blender Agent Skills | [EL4CTEO/blender-skills](https://github.com/EL4CTEO/blender-skills)，可运行其 [`install/install.ps1`](https://raw.githubusercontent.com/EL4CTEO/blender-skills/main/install/install.ps1) |

UE 5.7.4 通过 [Epic Games Launcher](https://www.unrealengine.com/download) 安装。`App` 使用 Go 1.26 构建，打包脚本需要 `go-winres`。

## 许可与致谢

角色模型来自 Sketchfab 的 Jun Hungry，采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。游戏本体资产版权归 S-Game 所有，本仓库不分发这些资产。本项目为非官方 MOD，与开发商和发行商无关。

## 开发

先阅读 [phantom-blade-zero-mod skill](.agents/skills/phantom-blade-zero-mod/SKILL.md)。脚本集中在该 skill 的 `scripts/`，使用功能名称，当前运行时截图由用户提供。
