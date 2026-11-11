# Nexus mod 页面文案（#948）

- 页面：https://www.nexusmods.com/phantombladezero/mods/948
- 编辑入口：https://www.nexusmods.com/games/phantombladezero/mods/948/edit/general
- 文件管理：https://www.nexusmods.com/games/phantombladezero/mods/948/edit/files

Nexus 后台的写接口（`POST /api/flamework/mods/save`）会被 Cloudflare managed challenge 拦下，页面内容只在编辑界面的表单里改。

## 表单字段

- Mod Name：Zero (Neverness to Everness) - Playable Protagonist Replacement
- 短描述（Nexus 落库会截到约 87 字符，只保留第一句）：
  Replaces Phantom Blade Zero's playable protagonist with Zero from Neverness to Everness. Install and uninstall with the included PBZModKit.
- Mod version：1.0.2
- Game / Category / Author / Language：Phantom Blade Zero / Characters / graydovee / Any
- Tags：Textures
- Generative AI usage：AI assisted with build and packaging scripts

## 文件

- 主文件：显示名 `PhantomBladeZero-NTE-Character-Mod-zzz_Nte_Zero_P`（历史记录名为 PhantomBladeZero-NTE-Zero-Mod，改名后保持同一文件记录），Category Main，每次版本更新用 Update existing file 覆盖并保留 Previous files。
- 上传包：`zzz_Nte_Zero_P-v{version}.zip`（三件套 + allowlist.json + mod.json + README.md + SHA256SUMS.txt），不含安装器。
- 同一时间只能装一个角色包：安装前先卸载其它角色 MOD（共用主角槽位）。

## 完整描述（BBCode）

[center][size=5][b]Zero from Neverness to Everness in Phantom Blade Zero[/b][/size][/center]

[size=4][b]Description[/b][/size]
This mod replaces Phantom Blade Zero's playable protagonist with Zero from Neverness to Everness, so you can play the game as Zero.

[size=4][b]Changes in 1.0.2[/b][/size]
- Repackaged for the multi-character release naming: the MOD id is now zzz_Nte_Zero_P.
- Game content is unchanged. The cooked mesh, textures and materials are byte-identical to 1.0.1; only the container name and version marker differ.

[size=4][b]Installation[/b][/size]
[b]1.[/b] Fully exit Phantom Blade Zero.
[b]2.[/b] Extract the archive anywhere and run [b]PBZModKit.exe[/b].
[b]3.[/b] If the game folder is not detected automatically, point the kit at your install (Steam or WeGame).
[b]4.[/b] Select [b]zzz_Nte_Zero_P[/b], install, then launch the game.

[b]Uninstall:[/b] open PBZModKit.exe again and uninstall the mod.

[size=4][b]Requirements[/b][/size]
- Phantom Blade Zero (Steam or WeGame), current version.
- Windows 10 or 11, 64-bit.

[size=4][b]Shout outs[/b][/size]
- Character model and textures: "Esper Zero Animated - Neverness To Everness" by [b]Jun Hungry[/b] on Sketchfab, licensed [b]CC BY 4.0[/b].

[size=4][b]Credits and license[/b][/size]
This is a free, non-official fan project and is not affiliated with S-Game or the model author. Game assets remain the property of S-Game. If you reuse the model, credit Jun Hungry and follow CC BY 4.0.

[center][size=5][b]影之刃零 · 异环·零 主角替换[/b][/size][/center]

[size=4][b]简介[/b][/size]
本 MOD 将《影之刃零》的可玩主角替换为《异环》的零，让玩家以零的身份游玩。

[size=4][b]1.0.2 改动[/b][/size]
- 配合多角色发行命名为 MOD id：zzz_Nte_Zero_P。
- 游戏内容不变：cooked 网格、贴图与材质与 1.0.1 逐字节一致，仅容器名与版本标记不同。

[size=4][b]安装[/b][/size]
[b]1.[/b] 完全退出游戏。
[b]2.[/b] 将压缩包解压到任意位置，运行 [b]PBZModKit.exe[/b]。
[b]3.[/b] 若未自动识别游戏目录，请手动指向游戏安装位置（Steam 或 WeGame）。
[b]4.[/b] 选择 [b]zzz_Nte_Zero_P[/b] 安装，然后启动游戏。

[b]卸载：[/b]再次打开 PBZModKit.exe，卸载该 MOD 即可。

[size=4][b]需求[/b][/size]
- 《影之刃零》（Steam 或 WeGame），当前版本。
- Windows 10 或 11，64 位。

[size=4][b]致谢[/b][/size]
- 角色模型与贴图：Sketchfab "Esper Zero Animated - Neverness To Everness"，作者 Jun Hungry，CC BY 4.0 许可。

[size=4][b]版权与许可[/b][/size]
本 MOD 为免费的非官方同人作品，与 S-Game 及模型作者无关。游戏资产版权归 S-Game 所有。如二次使用模型，请署名 Jun Hungry 并遵守 CC BY 4.0。
