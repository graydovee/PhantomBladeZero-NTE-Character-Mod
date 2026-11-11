package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"pbzmodkit/internal/discovery"
	"pbzmodkit/internal/install"
	"pbzmodkit/internal/modrepo"
)

// CLI 与 GUI 共用同一套配置和安装状态，这里只做参数解析与输出。
const cliUsage = `PBZModKit 命令行版

用法:
  PBZModKit-cli.exe <命令> [参数]

命令:
  list                     列出 <程序目录>\Mods 里的 mod 及安装状态
  status                   显示游戏路径 / mod 仓库 / ~mods 当前内容
  install <id|目录名>       安装指定 mod（同名互斥分组会拒绝）
  install <id> --force     覆盖安装（同一 mod 升级用）
  uninstall <id>           卸载并删除已安装文件
  restore                  还原所有已安装 mod
  setgame <路径>            设置游戏根目录（含 ProjectPBZ 的目录）
  setrepo <路径>            设置 mod 仓库目录（默认 <程序目录>\Mods）

示例:
  PBZModKit-cli.exe status
  PBZModKit-cli.exe install zzz_Nte_Zero_P
`

func runCLI(args []string) int {
	if len(args) == 0 {
		fmt.Print(cliUsage)
		return 0
	}
	cfg := install.LoadConfig()
	st := install.LoadState()

	gameRoot := ""
	if cfg.GameRoot != "" {
		gameRoot = cfg.GameRoot
	}
	repo := cfg.ModsRepo
	if repo == "" {
		exe, _ := os.Executable()
		repo = discovery.DefaultModsRepo(exe)
	}

	cmd := strings.ToLower(args[0])
	rest := args[1:]

	setGame := func(p string) {
		cfg.GameRoot = p
		_ = install.SaveConfig(cfg)
		gameRoot = p
	}

	switch cmd {
	case "help", "-h", "--help":
		fmt.Print(cliUsage)
		return 0

	case "setgame":
		if len(rest) == 0 {
			fmt.Fprintln(os.Stderr, "缺少路径")
			return 2
		}
		p := filepath.Clean(rest[0])
		if ok, reason := discovery.ValidateRoot(p); !ok {
			fmt.Fprintf(os.Stderr, "不是有效的游戏目录: %s\n", reason)
			return 1
		}
		setGame(p)
		fmt.Println("已设置游戏目录:", p)
		return 0

	case "setrepo":
		if len(rest) == 0 {
			fmt.Fprintln(os.Stderr, "缺少路径")
			return 2
		}
		cfg.ModsRepo = filepath.Clean(rest[0])
		_ = install.SaveConfig(cfg)
		fmt.Println("已设置 mod 仓库:", cfg.ModsRepo)
		return 0
	}

	// 以下命令需要游戏目录
	if gameRoot == "" {
		guess := `D:\Program Files (x86)\Steam\steamapps\common\PBZ`
		if ok, _ := discovery.ValidateRoot(guess); ok {
			gameRoot = guess
			fmt.Fprintln(os.Stderr, "[提示] 未配置游戏目录，先用自动探测到的:", guess)
		} else {
			fmt.Fprintln(os.Stderr, "未配置游戏目录，请先运行: PBZModKit-cli.exe setgame <路径>")
			return 1
		}
	}

	modsDir := discovery.ModsDir(gameRoot)
	paksDir := discovery.PaksDir(gameRoot)

	switch cmd {
	case "status":
		fmt.Println("游戏目录 :", gameRoot)
		fmt.Println("Paks     :", paksDir)
		fmt.Println("~mods    :", modsDir)
		fmt.Println("mod 仓库 :", repo)
		fmt.Println()
		fmt.Println("已安装（由本工具记录）:")
		if len(st.Installed) == 0 {
			fmt.Println("  (无)")
		}
		for _, m := range st.Installed {
			fmt.Printf("  %-24s %-20s %s\n", m.ModID, m.Name, m.InstalledAt.Format("2006-01-02 15:04"))
			for _, f := range m.Files {
				fmt.Printf("      - %s\n", f.Name)
			}
		}
		fmt.Println()
		fmt.Println("~mods 实际内容:")
		entries, err := os.ReadDir(modsDir)
		if err != nil || len(entries) == 0 {
			fmt.Println("  (空)")
		}
		for _, e := range entries {
			info, _ := e.Info()
			size := int64(0)
			if info != nil {
				size = info.Size()
			}
			kind := "file"
			if e.IsDir() {
				kind = "DIR(危险: 会被一起挂载)"
			}
			fmt.Printf("  %-28s %10.2f MB  %s\n", e.Name(), float64(size)/1024/1024, kind)
		}
		return 0

	case "list":
		mods, err := modrepo.Scan(repo)
		if err != nil {
			fmt.Fprintf(os.Stderr, "扫描仓库失败: %v\n", err)
			return 1
		}
		if len(mods) == 0 {
			fmt.Println("仓库里没有找到 mod:", repo)
			return 0
		}
		// 列宽按"终端显示宽度"计算（中文算 2 列），否则版本/大小这几列永远对不齐。
		fmt.Printf("%s %s %s %s %s %s %s\n",
			padRight("ID", 24), padRight("名称", 22), padLeft("版本", 12),
			padRight("作者", 12), padLeft("大小", 10), padRight("状态", 8), "说明")
		for _, m := range mods {
			status := "未安装"
			if st.Find(m.ID) != nil {
				status = "已安装"
			}
			note := strings.TrimSpace(m.Description)
			if m.Problem != "" {
				status = "不可用"
				note = m.Problem
			}
			if note == "" {
				note = "target=" + orDash(m.Target)
			}
			fmt.Printf("%s %s %s %s %s %s %s\n",
				padRight(m.ID, 24),
				padRight(m.Name, 22),
				padLeft(orDash(m.Version), 12),
				padRight(orText(m.Author, "未署名"), 12),
				padLeft(humanSize(m.TotalSize), 10),
				padRight(status, 8),
				truncDisplay(note, 60))
		}
		return 0

	case "install":
		if len(rest) == 0 {
			fmt.Fprintln(os.Stderr, "缺少 mod id")
			return 2
		}
		force := false
		id := rest[0]
		for _, a := range rest[1:] {
			if a == "--force" {
				force = true
			}
		}
		m, err := findMod(repo, id)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
		if err := install.Install(gameRoot, *m, st, force); err != nil {
			fmt.Fprintf(os.Stderr, "安装失败: %v\n", err)
			return 1
		}
		fmt.Printf("已安装 %s (%s)\n", m.ID, m.Name)
		return 0

	case "uninstall":
		if len(rest) == 0 {
			fmt.Fprintln(os.Stderr, "缺少 mod id")
			return 2
		}
		warns, err := install.Uninstall(gameRoot, rest[0], st)
		for _, w := range warns {
			fmt.Fprintln(os.Stderr, "[警告]", w)
		}
		if err != nil {
			fmt.Fprintf(os.Stderr, "卸载失败: %v\n", err)
			return 1
		}
		fmt.Println("已卸载", rest[0])
		return 0

	case "clean":
		// 状态丢失/手工拷过文件时的兜底：清空 ~mods 并清空记录，任何情况下都能回到原版
		entries, rerr := os.ReadDir(modsDir)
		if rerr != nil && !os.IsNotExist(rerr) {
			fmt.Fprintf(os.Stderr, "读取 ~mods 失败: %v\n", rerr)
			return 1
		}
		n := 0
		for _, e := range entries {
			p := filepath.Join(modsDir, e.Name())
			if err := os.RemoveAll(p); err != nil {
				fmt.Fprintf(os.Stderr, "删除失败 %s: %v\n", p, err)
				continue
			}
			n++
		}
		st.Installed = nil
		_ = st.Save()
		fmt.Printf("已清空 ~mods（删除 %d 项）并清空安装记录，游戏回到无 mod 状态\n", n)
		return 0

	case "restore":
		warns, err := install.RestoreAll(gameRoot, st)
		for _, w := range warns {
			fmt.Fprintln(os.Stderr, "[警告]", w)
		}
		if err != nil {
			fmt.Fprintf(os.Stderr, "还原失败: %v\n", err)
			return 1
		}
		fmt.Println("已还原所有已安装 mod")
		return 0
	}

	fmt.Fprintf(os.Stderr, "未知命令: %s\n\n", cmd)
	fmt.Print(cliUsage)
	return 2
}

func findMod(repo, id string) (*modrepo.Mod, error) {
	mods, err := modrepo.Scan(repo)
	if err != nil {
		return nil, fmt.Errorf("扫描仓库失败: %w", err)
	}
	var hits []modrepo.Mod
	for _, m := range mods {
		if strings.EqualFold(m.ID, id) || strings.EqualFold(filepath.Base(m.Dir), id) {
			hits = append(hits, m)
		}
	}
	if len(hits) == 0 {
		var ids []string
		for _, m := range mods {
			ids = append(ids, m.ID)
		}
		sort.Strings(ids)
		return nil, fmt.Errorf("仓库里找不到 %q，可用: %s", id, strings.Join(ids, ", "))
	}
	if len(hits) > 1 {
		return nil, fmt.Errorf("%q 匹配到多个 mod，请用完整目录名", id)
	}
	return &hits[0], nil
}

func orDash(s string) string {
	if s == "" {
		return "-"
	}
	return s
}

func orText(s, alt string) string {
	if strings.TrimSpace(s) == "" {
		return alt
	}
	return s
}

// humanSize 与 GUI 使用同一套单位，保证两边看到的数字一致。
func humanSize(n int64) string {
	const unit = 1024
	if n < unit {
		return fmt.Sprintf("%d B", n)
	}
	div, exp := int64(unit), 0
	for v := n / unit; v >= unit; v /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(n)/float64(div), "KMGT"[exp])
}

// runeWidth 返回一个字符在等宽终端里占几列：CJK/全角/emoji 算 2，其余算 1。
// 只用 printf 的 %-20s 是靠字符数补空格的，中英混排时列会歪，所以自己算宽度。
func runeWidth(r rune) int {
	switch {
	case r == 0 || r < 0x20 || (r >= 0x7F && r < 0xA0):
		return 0
	case r >= 0x1100 && r <= 0x115F, // Hangul Jamo
		r == 0x2329, r == 0x232A,
		r >= 0x2E80 && r <= 0xA4CF && r != 0x303F, // CJK 部首、假名、汉字
		r >= 0xAC00 && r <= 0xD7A3,                // Hangul Syllables
		r >= 0xF900 && r <= 0xFAFF,                // CJK 兼容汉字
		r >= 0xFE10 && r <= 0xFE19,
		r >= 0xFE30 && r <= 0xFE6F,
		r >= 0xFF00 && r <= 0xFF60, // 全角字符
		r >= 0xFFE0 && r <= 0xFFE6,
		r >= 0x1F300 && r <= 0x1F64F,
		r >= 0x1F900 && r <= 0x1F9FF,
		r >= 0x20000 && r <= 0x3FFFD:
		return 2
	}
	return 1
}

func displayWidth(s string) int {
	w := 0
	for _, r := range s {
		w += runeWidth(r)
	}
	return w
}

// truncDisplay 按显示宽度截断，超宽时以 "…" 结尾。
func truncDisplay(s string, width int) string {
	if displayWidth(s) <= width {
		return s
	}
	var b strings.Builder
	w := 0
	for _, r := range s {
		rw := runeWidth(r)
		if w+rw > width-1 {
			break
		}
		b.WriteRune(r)
		w += rw
	}
	b.WriteString("…")
	return b.String()
}

// padRight 左对齐补到 width 列；padLeft 右对齐（数字用）。
func padRight(s string, width int) string {
	s = truncDisplay(s, width)
	if pad := width - displayWidth(s); pad > 0 {
		return s + strings.Repeat(" ", pad)
	}
	return s
}

func padLeft(s string, width int) string {
	s = truncDisplay(s, width)
	if pad := width - displayWidth(s); pad > 0 {
		return strings.Repeat(" ", pad) + s
	}
	return s
}
