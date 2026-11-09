package discovery

import (
	"regexp"
	"strings"
)

var (
	rePathLine  = regexp.MustCompile(`(?mi)^\s*"path"\s+"((?:[^"\\]|\\.)*)"`)
	reIndexLine = regexp.MustCompile(`(?mi)^\s*"\d+"\s+"((?:[^"\\]|\\.)*)"`)
)

// ParseLibraryPaths 从 steamapps\libraryfolders.vdf 中取出所有库路径。
// 新格式是 "path" "D:\\Games\\Steam"，老格式是 "1" "D:\\Games"。
func ParseLibraryPaths(vdf string) []string {
	seen := make(map[string]bool)
	out := make([]string, 0, 4)
	add := func(s string) {
		p := strings.TrimSpace(UnescapeVDF(s))
		if p == "" {
			return
		}
		k := strings.ToLower(p)
		if seen[k] {
			return
		}
		seen[k] = true
		out = append(out, p)
	}
	for _, m := range rePathLine.FindAllStringSubmatch(vdf, -1) {
		add(m[1])
	}
	if len(out) == 0 {
		for _, m := range reIndexLine.FindAllStringSubmatch(vdf, -1) {
			add(m[1])
		}
	}
	return out
}

// UnescapeVDF 处理 VDF 里的 \\ 与 \" 转义。
func UnescapeVDF(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for i := 0; i < len(s); i++ {
		if s[i] == '\\' && i+1 < len(s) {
			i++
			switch s[i] {
			case 'n':
				b.WriteByte('\n')
			case 't':
				b.WriteByte('\t')
			default:
				b.WriteByte(s[i])
			}
			continue
		}
		b.WriteByte(s[i])
	}
	return b.String()
}
