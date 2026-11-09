package discovery

import (
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/sys/windows/registry"
)

// wegameDataRoots 找出 WeGame 的数据根目录（里面含 rail_apps / common_apps）。
// WeGame 的注册表 Apps 子键只有公共运行库，游戏清单拿不到，因此必须扫目录。
func wegameDataRoots() []string {
	seen := make(map[string]bool)
	var out []string
	add := func(p string) {
		p = filepath.Clean(strings.ReplaceAll(strings.TrimSpace(p), "/", `\`))
		if p == "" || p == `.` {
			return
		}
		st, err := os.Stat(p)
		if err != nil || !st.IsDir() {
			return
		}
		k := strings.ToLower(p)
		if seen[k] {
			return
		}
		seen[k] = true
		out = append(out, p)
	}

	// 注册表里可能是 InstallPath / WeGamePath / DataPath 等，逐个值试
	for _, key := range []string{`SOFTWARE\WOW6432Node\Tencent\WeGame`, `SOFTWARE\Tencent\WeGame`} {
		for _, hive := range []registry.Key{registry.LOCAL_MACHINE, registry.CURRENT_USER} {
			k, err := registry.OpenKey(hive, key, registry.QUERY_VALUE)
			if err != nil {
				continue
			}
			names, _ := k.ReadValueNames(0)
			for _, n := range names {
				if v, _, err := k.GetStringValue(n); err == nil {
					add(v)
					add(filepath.Join(v, "WeGameApps"))
				}
			}
			k.Close()
		}
	}

	for _, p := range []string{
		`C:\Program Files\WeGame`, `C:\Program Files (x86)\WeGame`,
		`D:\WeGame`, `D:\Program Files\WeGame`, `D:\Program Files (x86)\WeGame`,
	} {
		add(p)
		add(filepath.Join(p, "WeGameApps"))
	}
	for _, d := range fixedDrives() {
		add(filepath.Join(d, "WeGameApps"))
		add(filepath.Join(d, "WeGame"))
	}
	return out
}

// FromWeGame 在 WeGame 数据根下的 rail_apps / common_apps 里找游戏。
func FromWeGame() []GameInstall {
	seen := make(map[string]bool)
	var out []GameInstall
	push := func(p string) {
		key := strings.ToLower(p)
		if seen[key] {
			return
		}
		seen[key] = true
		out = append(out, GameInstall{Root: p, Source: "WeGame", UTOC: CountUTOC(p)})
	}

	for _, root := range wegameDataRoots() {
		for _, sub := range []string{"rail_apps", "common_apps", filepath.Join("rail_apps", "common")} {
			dir := filepath.Join(root, sub)
			entries, err := os.ReadDir(dir)
			if err != nil {
				continue
			}
			for _, e := range entries {
				if !e.IsDir() {
					continue
				}
				p := filepath.Join(dir, e.Name())
				if ok, _ := ValidateRoot(p); ok {
					push(p)
					continue
				}
				// 有些游戏多套一层目录
				inner, err := os.ReadDir(p)
				if err != nil {
					continue
				}
				for _, ie := range inner {
					if !ie.IsDir() {
						continue
					}
					q := filepath.Join(p, ie.Name())
					if ok, _ := ValidateRoot(q); ok {
						push(q)
					}
				}
			}
		}
	}
	return out
}
