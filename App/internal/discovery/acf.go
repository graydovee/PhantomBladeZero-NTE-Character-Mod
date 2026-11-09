package discovery

import "regexp"

var reACF = regexp.MustCompile(`(?m)^\s*"([^"]+)"\s+"([^"]*)"`)

// ParseACF 把 appmanifest_*.acf 里的 "key" "value" 收成 map（同名键保留第一次出现的值）。
func ParseACF(s string) map[string]string {
	out := make(map[string]string, 16)
	for _, m := range reACF.FindAllStringSubmatch(s, -1) {
		k, v := m[1], m[2]
		if _, ok := out[k]; !ok {
			out[k] = v
		}
	}
	return out
}
