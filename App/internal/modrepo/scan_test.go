package modrepo

import (
	"os"
	"path/filepath"
	"testing"
)

func writeFile(t *testing.T, p string, data string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte(data), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestScanFindsModWithManifest(t *testing.T) {
	repo := t.TempDir()
	modDir := filepath.Join(repo, "my_mod")
	writeFile(t, filepath.Join(modDir, "mod.json"), `{
		"id":"my_mod","name":"测试 Mod","version":"1.2.3","target":"hero","author":"tester"
	}`)
	writeFile(t, filepath.Join(modDir, "aaa_bbb_P.utoc"), "utoc")
	writeFile(t, filepath.Join(modDir, "aaa_bbb_P.ucas"), "ucas-data")

	mods, err := Scan(repo)
	if err != nil {
		t.Fatal(err)
	}
	if len(mods) != 1 {
		t.Fatalf("应找到 1 个 mod，实际 %d", len(mods))
	}
	m := mods[0]
	if m.ID != "my_mod" || m.Name != "测试 Mod" || m.Version != "1.2.3" || m.Target != "hero" {
		t.Fatalf("manifest 未生效: %+v", m)
	}
	if !m.HasManifest {
		t.Fatal("HasManifest 应为 true")
	}
	if m.Problem != "" {
		t.Fatalf("不该有问题: %s", m.Problem)
	}
	if m.TotalSize <= 0 {
		t.Fatal("TotalSize 应大于 0")
	}
	files := m.ContainerFiles()
	if len(files) != 2 {
		t.Fatalf("容器文件应有 2 个，实际 %v", files)
	}
}

func TestScanDetectsMissingUCAS(t *testing.T) {
	repo := t.TempDir()
	modDir := filepath.Join(repo, "broken")
	writeFile(t, filepath.Join(modDir, "only.utoc"), "utoc")

	mods, err := Scan(repo)
	if err != nil {
		t.Fatal(err)
	}
	if len(mods) != 1 {
		t.Fatalf("应找到 1 个目录，实际 %d", len(mods))
	}
	if mods[0].Problem == "" {
		t.Fatal("缺 .ucas 时应标记问题")
	}
}

func TestScanSkipsNonModDirs(t *testing.T) {
	repo := t.TempDir()
	writeFile(t, filepath.Join(repo, "readme.txt"), "hello")
	writeFile(t, filepath.Join(repo, "_disabled", "x.utoc"), "x")
	if err := os.MkdirAll(filepath.Join(repo, "empty_dir"), 0o755); err != nil {
		t.Fatal(err)
	}
	mods, err := Scan(repo)
	if err != nil {
		t.Fatal(err)
	}
	if len(mods) != 0 {
		t.Fatalf("不该找到 mod，实际 %d: %+v", len(mods), mods)
	}
}

func TestScanNestedContainers(t *testing.T) {
	repo := t.TempDir()
	modDir := filepath.Join(repo, "nested")
	writeFile(t, filepath.Join(modDir, "sub", "deep.utoc"), "utoc")
	writeFile(t, filepath.Join(modDir, "sub", "deep.ucas"), "ucas")
	mods, err := Scan(repo)
	if err != nil {
		t.Fatal(err)
	}
	if len(mods) != 1 || len(mods[0].Bases) != 1 {
		t.Fatalf("应识别嵌套容器: %+v", mods)
	}
}
