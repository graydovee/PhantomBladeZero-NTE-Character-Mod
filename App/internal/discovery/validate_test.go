package discovery

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParseACF(t *testing.T) {
	acf := `"AppState"
{
	"appid"		"4115450"
	"name"		"Phantom Blade Zero"
	"installdir"		"PBZ"
	"StateFlags"		"4"
	"buildid"		"26367565"
	"InstalledDepots"
	{
		"4115451"
		{
			"name"		"nested-should-not-win"
		}
	}
}`
	m := ParseACF(acf)
	if m["appid"] != "4115450" {
		t.Fatalf("appid: %q", m["appid"])
	}
	if m["installdir"] != "PBZ" {
		t.Fatalf("installdir: %q", m["installdir"])
	}
	if m["buildid"] != "26367565" {
		t.Fatalf("buildid: %q", m["buildid"])
	}
	if m["name"] != "Phantom Blade Zero" {
		t.Fatalf("name 应保留第一次出现的值: %q", m["name"])
	}
}

// makeFakeGame 造一个结构正确的假游戏目录。
func makeFakeGame(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	paks := filepath.Join(root, "ProjectPBZ", "Content", "Paks")
	if err := os.MkdirAll(paks, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(paks, "ProjectPBZ-Windows.utoc"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "platform", "steam"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "platform", "steam", "PBZ.exe"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	return root
}

func TestValidateRootOK(t *testing.T) {
	root := makeFakeGame(t)
	ok, reason := ValidateRoot(root)
	if !ok {
		t.Fatalf("应该识别为游戏目录，却失败: %s", reason)
	}
	if CountUTOC(root) != 1 {
		t.Fatalf("utoc 计数应为 1，实际 %d", CountUTOC(root))
	}
	if got, want := ModsDir(root), filepath.Join(root, "ProjectPBZ", "Content", "Paks", "~mods"); got != want {
		t.Fatalf("~mods 路径不对: %q", got)
	}
}

func TestValidateRootRejects(t *testing.T) {
	cases := map[string]string{
		"空路径":   "",
		"不存在":   filepath.Join(t.TempDir(), "nope"),
		"空目录":   t.TempDir(),
	}
	for name, p := range cases {
		if ok, _ := ValidateRoot(p); ok {
			t.Fatalf("%s 不应通过校验: %q", name, p)
		}
	}
}

func TestValidateRootWithoutUTOC(t *testing.T) {
	root := t.TempDir()
	paks := filepath.Join(root, "ProjectPBZ", "Content", "Paks")
	if err := os.MkdirAll(paks, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "platform", "steam"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "platform", "steam", "PBZ.exe"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	if ok, reason := ValidateRoot(root); ok {
		t.Fatalf("没有 .utoc 不应通过，reason=%s", reason)
	}
}
