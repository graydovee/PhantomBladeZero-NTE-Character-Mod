package discovery

import (
	"os"
	"path/filepath"
	"strings"
)

// ValidateRoot 判断 p 是否是《影之刃零》的安装根目录。
// 只认目录结构，不认名字 —— 避免误判同名 demo / 备份目录。
func ValidateRoot(p string) (bool, string) {
	if strings.TrimSpace(p) == "" {
		return false, "路径为空"
	}
	st, err := os.Stat(p)
	if err != nil || !st.IsDir() {
		return false, "目录不存在"
	}
	paks := filepath.Join(p, "ProjectPBZ", "Content", "Paks")
	st, err = os.Stat(paks)
	if err != nil || !st.IsDir() {
		return false, `缺少 ProjectPBZ\Content\Paks`
	}
	if CountUTOC(p) == 0 {
		return false, "Paks 目录下没有 .utoc 容器"
	}
	// 至少要有可执行文件或 Binaries 目录，进一步排除残缺副本
	if _, err := os.Stat(filepath.Join(p, "platform", "steam", "PBZ.exe")); err != nil {
		if _, err2 := os.Stat(filepath.Join(p, "ProjectPBZ", "Binaries", "Win64")); err2 != nil {
			return false, "缺少 platform\\steam\\PBZ.exe 与 Binaries 目录"
		}
	}
	return true, ""
}

// CountUTOC 统计 Paks 目录下的 .utoc 数量（游戏主容器至少有一个）。
func CountUTOC(root string) int {
	paks := filepath.Join(root, "ProjectPBZ", "Content", "Paks")
	entries, err := os.ReadDir(paks)
	if err != nil {
		return 0
	}
	n := 0
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		if strings.EqualFold(filepath.Ext(e.Name()), ".utoc") {
			n++
		}
	}
	return n
}

// PaksDir 返回 <game>\ProjectPBZ\Content\Paks。
func PaksDir(root string) string {
	return filepath.Join(root, "ProjectPBZ", "Content", "Paks")
}

// ModsDir 返回 mod 安装目录 <game>\ProjectPBZ\Content\Paks\~mods。
func ModsDir(root string) string {
	return filepath.Join(PaksDir(root), "~mods")
}
