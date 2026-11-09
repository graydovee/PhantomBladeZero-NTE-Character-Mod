package modrepo

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// Manifest 是 mod 目录下可选的 mod.json。
type Manifest struct {
	ID           string   `json:"id"`
	Name         string   `json:"name"`
	Version      string   `json:"version"`
	Author       string   `json:"author"`
	Description  string   `json:"description"`
	Target       string   `json:"target"`       // 互斥分组，例如 hero
	RequiresBuild string  `json:"requires_build"`
	Files        []string `json:"files"`
}

// Mod 表示仓库里的一个 mod（一个一级子目录）。
type Mod struct {
	ID          string
	Name        string
	Version     string
	Author      string
	Description string
	Target      string
	Dir         string
	Bases       []string // 不带扩展名的容器基名（绝对路径）
	TotalSize   int64
	HasManifest bool
	Problem     string // 非空表示这个 mod 不完整，不能安装
}

// Scan 扫描仓库根目录下的每个一级子目录，识别其中的 .utoc/.ucas 容器。
func Scan(root string) ([]Mod, error) {
	entries, err := os.ReadDir(root)
	if err != nil {
		return nil, err
	}
	var mods []Mod
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		name := e.Name()
		if strings.HasPrefix(name, ".") || strings.HasPrefix(name, "_") {
			continue
		}
		m := scanOne(filepath.Join(root, name))
		if m == nil {
			continue
		}
		mods = append(mods, *m)
	}
	sort.SliceStable(mods, func(i, j int) bool { return strings.ToLower(mods[i].Name) < strings.ToLower(mods[j].Name) })
	return mods, nil
}

func scanOne(dir string) *Mod {
	m := &Mod{Dir: dir, Name: filepath.Base(dir), ID: filepath.Base(dir)}

	if b, err := os.ReadFile(filepath.Join(dir, "mod.json")); err == nil {
		var mf Manifest
		if json.Unmarshal(b, &mf) == nil {
			m.HasManifest = true
			if mf.ID != "" {
				m.ID = mf.ID
			}
			if mf.Name != "" {
				m.Name = mf.Name
			}
			m.Version = mf.Version
			m.Author = mf.Author
			m.Description = mf.Description
			m.Target = mf.Target
		}
	}

	bases := findUTOCBases(dir, 4)
	if len(bases) == 0 {
		return nil // 不是 mod 目录，忽略
	}
	m.Bases = bases
	for _, base := range bases {
		for _, ext := range []string{".utoc", ".ucas", ".pak"} {
			if st, err := os.Stat(base + ext); err == nil {
				m.TotalSize += st.Size()
			}
		}
		if _, err := os.Stat(base + ".ucas"); err != nil {
			m.Problem = "缺少同名 .ucas（容器不完整）"
		}
	}
	return m
}

// findUTOCBases 在 dir 下（含子目录）找 .utoc，返回不带扩展名的绝对路径基名。
func findUTOCBases(dir string, maxDepth int) []string {
	var out []string
	var walk func(string, int)
	walk = func(d string, depth int) {
		entries, err := os.ReadDir(d)
		if err != nil {
			return
		}
		for _, e := range entries {
			p := filepath.Join(d, e.Name())
			if e.IsDir() {
				if depth < maxDepth && !strings.HasPrefix(e.Name(), ".") {
					walk(p, depth+1)
				}
				continue
			}
			if strings.EqualFold(filepath.Ext(e.Name()), ".utoc") {
				out = append(out, strings.TrimSuffix(p, filepath.Ext(p)))
			}
		}
	}
	walk(dir, 0)
	sort.Strings(out)
	return out
}

// ContainerFiles 返回这个 mod 需要安装的文件名列表（.utoc / .ucas / 可选 .pak）。
func (m Mod) ContainerFiles() []string {
	var out []string
	for _, base := range m.Bases {
		for _, ext := range []string{".utoc", ".ucas", ".pak"} {
			if _, err := os.Stat(base + ext); err == nil {
				out = append(out, filepath.Base(base)+ext)
			}
		}
	}
	return out
}
