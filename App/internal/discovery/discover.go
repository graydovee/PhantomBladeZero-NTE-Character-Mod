package discovery

import (
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// GameInstall 表示一个被识别出来的游戏安装。
type GameInstall struct {
	Root    string // 游戏根目录
	Source  string // Steam / WeGame / 扫描 / 手动
	BuildID string // Steam 的 buildid（WeGame 版可能为空）
	UTOC    int    // Paks 下的 .utoc 数量
}

// DiscoverAll 依次尝试 Steam、WeGame、磁盘扫描，去重后返回。
func DiscoverAll() []GameInstall {
	var all []GameInstall
	all = append(all, FromSteam()...)
	all = append(all, FromWeGame()...)
	all = append(all, scanDrives()...)

	seen := make(map[string]int)
	var out []GameInstall
	for _, g := range all {
		k := strings.ToLower(filepath.Clean(g.Root))
		if i, ok := seen[k]; ok {
			if out[i].BuildID == "" {
				out[i].BuildID = g.BuildID
			}
			continue
		}
		seen[k] = len(out)
		out = append(out, g)
	}
	sort.SliceStable(out, func(i, j int) bool { return strings.ToLower(out[i].Root) < strings.ToLower(out[j].Root) })
	return out
}

// fixedDrives 返回存在的本地盘符（如 "C:\", "D:\"）。
func fixedDrives() []string {
	var out []string
	for c := 'A'; c <= 'Z'; c++ {
		p := string(c) + `:\`
		if st, err := os.Stat(p); err == nil && st.IsDir() {
			out = append(out, p)
		}
	}
	return out
}

func dedupePaths(in []string) []string {
	seen := make(map[string]bool)
	out := make([]string, 0, len(in))
	for _, p := range in {
		if strings.TrimSpace(p) == "" {
			continue
		}
		k := strings.ToLower(filepath.Clean(p))
		if seen[k] {
			continue
		}
		seen[k] = true
		out = append(out, filepath.Clean(p))
	}
	return out
}

var skipDirNames = map[string]bool{
	"windows": true, "$recycle.bin": true, "system volume information": true,
	"recovery": true, "perf logs": true, "programdata": true, "appdata": true,
	"node_modules": true, ".git": true, "__pycache__": true, "winsxs": true,
	"installer": true, "temp": true, "tmp": true, "cache": true,
	"windowsapps": true, "onedrivetemp": true, "msocache": true,
}

// scanDrives 做有界 BFS：深度 <= 4、节点 <= 4 万，遇到 ProjectPBZ 特征才校验。
func scanDrives() []GameInstall {
	var out []GameInstall
	const maxDepth = 4
	const maxNodes = 40000

	type node struct {
		dir   string
		depth int
	}
	nodes := 0
	queue := make([]node, 0, 64)
	for _, d := range fixedDrives() {
		queue = append(queue, node{dir: d, depth: 0})
	}

	for len(queue) > 0 && nodes < maxNodes {
		cur := queue[0]
		queue = queue[1:]
		nodes++

		// 便宜的特征判断：有 ProjectPBZ\Content\Paks 才值得完整校验
		if _, err := os.Stat(filepath.Join(cur.dir, "ProjectPBZ", "Content", "Paks")); err == nil {
			if ok, _ := ValidateRoot(cur.dir); ok {
				out = append(out, GameInstall{Root: cur.dir, Source: "扫描", UTOC: CountUTOC(cur.dir)})
			}
		}
		if cur.depth >= maxDepth {
			continue
		}

		entries, err := os.ReadDir(cur.dir)
		if err != nil {
			continue
		}
		for _, e := range entries {
			if !e.IsDir() {
				continue
			}
			name := strings.ToLower(e.Name())
			if skipDirNames[name] || strings.HasPrefix(name, ".") {
				continue
			}
			queue = append(queue, node{dir: filepath.Join(cur.dir, e.Name()), depth: cur.depth + 1})
		}
	}
	return out
}

// DefaultModsRepo 推断 mod 仓库目录：**程序所在目录**下的 Mods。
// 即 Release\PBZModKit.exe → Release\Mods；不看当前工作目录，也不向上找，
// 否则当程序所在目录本身叫 Mods（如 D:\Soft\Mods\PBZModKit.exe）时会误判成上一级。
func DefaultModsRepo(exePath string) string {
	return filepath.Join(filepath.Dir(exePath), "Mods")
}
