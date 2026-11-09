package discovery

import (
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/sys/windows/registry"
)

// PBZAppID 是《影之刃零》的 Steam AppID。
const PBZAppID = "4115450"

// steamRoots 找出 Steam 客户端安装目录（注册表多路探测）。
func steamRoots() []string {
	seen := make(map[string]bool)
	var out []string
	add := func(p string) {
		p = filepath.Clean(strings.ReplaceAll(strings.TrimSpace(p), "/", `\`))
		if p == "" {
			return
		}
		if st, err := os.Stat(p); err != nil || !st.IsDir() {
			return
		}
		k := strings.ToLower(p)
		if seen[k] {
			return
		}
		seen[k] = true
		out = append(out, p)
	}

	if k, err := registry.OpenKey(registry.CURRENT_USER, `Software\Valve\Steam`, registry.QUERY_VALUE); err == nil {
		if v, _, err := k.GetStringValue("SteamPath"); err == nil {
			add(v)
		}
		k.Close()
	}
	for _, key := range []string{`SOFTWARE\WOW6432Node\Valve\Steam`, `SOFTWARE\Valve\Steam`} {
		if k, err := registry.OpenKey(registry.LOCAL_MACHINE, key, registry.QUERY_VALUE); err == nil {
			if v, _, err := k.GetStringValue("InstallPath"); err == nil {
				add(v)
			}
			k.Close()
		}
	}
	return out
}

// FromSteam 遍历所有 Steam 库，返回识别到的游戏。
func FromSteam() []GameInstall {
	var out []GameInstall
	seen := make(map[string]bool)

	for _, steamRoot := range steamRoots() {
		libs := []string{steamRoot}
		vdfPath := filepath.Join(steamRoot, "steamapps", "libraryfolders.vdf")
		if b, err := os.ReadFile(vdfPath); err == nil {
			libs = append(libs, ParseLibraryPaths(string(b))...)
		}

		for _, lib := range dedupePaths(libs) {
			common := filepath.Join(lib, "steamapps", "common")
			installdir := "PBZ"
			build := ""

			acfPath := filepath.Join(lib, "steamapps", "appmanifest_"+PBZAppID+".acf")
			if b, err := os.ReadFile(acfPath); err == nil {
				m := ParseACF(string(b))
				if v := strings.TrimSpace(m["installdir"]); v != "" {
					installdir = v
				}
				build = strings.TrimSpace(m["buildid"])
			}

			cand := filepath.Join(common, installdir)
			if ok, _ := ValidateRoot(cand); ok {
				key := strings.ToLower(cand)
				if !seen[key] {
					seen[key] = true
					out = append(out, GameInstall{Root: cand, Source: "Steam", BuildID: build, UTOC: CountUTOC(cand)})
				}
				continue
			}

			// 兜底：common 下一层逐个试（应对 installdir 与 ACF 不一致的情况）
			entries, err := os.ReadDir(common)
			if err != nil {
				continue
			}
			for _, e := range entries {
				if !e.IsDir() {
					continue
				}
				p := filepath.Join(common, e.Name())
				ok, _ := ValidateRoot(p)
				if !ok {
					continue
				}
				key := strings.ToLower(p)
				if seen[key] {
					continue
				}
				seen[key] = true
				out = append(out, GameInstall{Root: p, Source: "Steam", BuildID: build, UTOC: CountUTOC(p)})
			}
		}
	}
	return out
}
