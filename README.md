# 影之刃零 × 异环·零

使用《影之刃零》原生 `Hun_Skin_Skeleton`，将可玩主角「魂」替换为《异环》女主「零」的角色替换 MOD。工程包含模型、材质、骨骼适配、动画驱动、IoStore 打包管线和 PBZModKit 源码。

仓库只保存源码、文档和制作 skill；角色模型、游戏原生资产与制作中间文件在本地取得，不随仓库分发。

## 下载与安装

发布包在 GitHub Release 中提供：

<https://github.com/graydovee/PhantomBladeZero-NTE-Zero-Mod/releases>

下载 `PhantomBladeZero-NTE-Zero-Mod-v1.0.0.zip` 并解压。安装器位于压缩包内的 `Release/PBZModKit.exe`，命令行版本为 `Release/PBZModKit-cli.exe`：

```powershell
& Release/PBZModKit-cli.exe status
& Release/PBZModKit-cli.exe install zzz_NteZeroNative_P
```

安装前必须完全退出游戏。`Release/data/` 是安装器本地状态目录，不包含在发布包中。参考 MOD、当前零 MOD 和安装器也分别提供了独立下载包。

## 恢复制作环境

克隆后按顺序补齐本地资产，工程才能打开和重新打包。

| 资产 | 来源 | 落盘位置 |
|---|---|---|
| 角色模型与贴图 | Sketchfab [Esper Zero Animated - Neverness To Everness](https://sketchfab.com/3d-models/esper-zero-animated-neverness-to-everness-1ada850ff2de4d3d8a317052c2144a88)，作者 Jun Hungry，CC BY 4.0 | `Pipeline/native-zero/model/zero/character.fbx` 与 `model/zero/textures/` 下的 16 张贴图 |
| 游戏原生资产 | 本机合法《影之刃零》客户端，用 `Tools/SkelDump` 提取 | `Pipeline/native-zero/model/game/` 与 `Pipeline/native-zero/unreal/ProjectPBZ/Plugins/HuaShira/` |
| 原生骨架与网格参考数据 | 同一客户端，`SkelDump meshrich` 与 `SkelDump props` | `Pipeline/native-zero/reference/native_body_mesh.json`、`native_skeleton_props.json` |
| 摆姿工作文件 | skill 的 `make_native_blank.py` 与 `build_native_mesh.py` 生成 | `Pipeline/native-zero/source/` 下的 `SK_ZeroBody_posed.blend`、`native_blank.fbx`、`native_blank_static.fbx` |
| 原生骨架 FBX | 同一客户端提取 | `Pipeline/native-zero/blender/game/game_rig_264.fbx` |
| 工程内资产 | 按 skill 第 6 步导入 FBX 后在编辑器中生成 | `Pipeline/native-zero/unreal/ProjectPBZ/Content/PBZContent/` |

`model/zero/textures/` 需要保持这些文件名：`T_player_051_female_{1,2}_{d,n,m,id}.png`、`T_player_009_female_hair_0{1,2}_{d,m}.png`、`T_player_051_female_face_{d,m,r}.png`、`T_player_051_female_eye_d.png`。

游戏原生 PAK、AES、USMAP 同样来自本机安装，命令见 [workflow.md](.agents/skills/phantom-blade-zero-mod/references/workflow.md)。

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
