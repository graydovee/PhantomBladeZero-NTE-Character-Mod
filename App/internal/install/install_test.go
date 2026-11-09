package install

import (
	"os"
	"path/filepath"
	"testing"

	"pbzmodkit/internal/discovery"
	"pbzmodkit/internal/modrepo"
)

func setup(t *testing.T) (gameRoot string, m modrepo.Mod) {
	t.Helper()
	t.Setenv("LOCALAPPDATA", t.TempDir())       // 隔离 state.json / config.json
	t.Setenv("PBZMODKIT_DATA_DIR", t.TempDir()) // DataDir 优先 exe 目录，必须显式指定才真正隔离

	gameRoot = t.TempDir()
	paks := filepath.Join(gameRoot, "ProjectPBZ", "Content", "Paks")
	if err := os.MkdirAll(paks, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(paks, "ProjectPBZ-Windows.utoc"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(gameRoot, "platform", "steam"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(gameRoot, "platform", "steam", "PBZ.exe"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}

	modDir := t.TempDir()
	base := filepath.Join(modDir, "zzz_Test_P")
	if err := os.WriteFile(base+".utoc", []byte("utoc-content"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(base+".ucas", []byte("ucas-content-longer"), 0o644); err != nil {
		t.Fatal(err)
	}

	m = modrepo.Mod{
		ID:    "zzz_Test_P",
		Name:  "测试 Mod",
		Dir:   modDir,
		Bases: []string{base},
	}
	return gameRoot, m
}

func TestInstallThenUninstall(t *testing.T) {
	gameRoot, m := setup(t)
	st := LoadState()

	if err := Install(gameRoot, m, st, false); err != nil {
		t.Fatalf("安装失败: %v", err)
	}
	modsDir := discovery.ModsDir(gameRoot)
	for _, n := range []string{"zzz_Test_P.utoc", "zzz_Test_P.ucas"} {
		if _, err := os.Stat(filepath.Join(modsDir, n)); err != nil {
			t.Fatalf("安装后缺少 %s: %v", n, err)
		}
	}
	if st.Find("zzz_Test_P") == nil {
		t.Fatal("状态里没有记录")
	}

	// 重新加载状态，确认已持久化
	st2 := LoadState()
	if st2.Find("zzz_Test_P") == nil {
		t.Fatal("状态没有落盘")
	}

	warns, err := Uninstall(gameRoot, "zzz_Test_P", st2)
	if err != nil {
		t.Fatalf("卸载失败: %v", err)
	}
	if len(warns) != 0 {
		t.Fatalf("不该有警告: %v", warns)
	}
	for _, n := range []string{"zzz_Test_P.utoc", "zzz_Test_P.ucas"} {
		if _, err := os.Stat(filepath.Join(modsDir, n)); !os.IsNotExist(err) {
			t.Fatalf("卸载后仍存在 %s", n)
		}
	}
	if LoadState().Find("zzz_Test_P") != nil {
		t.Fatal("卸载后状态未清除")
	}
}

func TestConflictSameTarget(t *testing.T) {
	gameRoot, m := setup(t)
	st := LoadState()
	m.Target = "hero"
	if err := Install(gameRoot, m, st, false); err != nil {
		t.Fatalf("第一次安装失败: %v", err)
	}

	// 另一个同 target 的 mod
	other := m
	other.ID = "other_mod"
	other.Name = "另一个主角替换"
	err := Install(gameRoot, other, st, false)
	if err == nil {
		t.Fatal("同 target 应冲突")
	}
	if _, ok := err.(*ConflictError); !ok {
		t.Fatalf("应是 ConflictError，实际 %T: %v", err, err)
	}
}

func TestOccupiedByOther(t *testing.T) {
	gameRoot, m := setup(t)
	st := LoadState()
	modsDir := discovery.ModsDir(gameRoot)
	if err := os.MkdirAll(modsDir, 0o755); err != nil {
		t.Fatal(err)
	}
	// 用户手动放的同名文件
	if err := os.WriteFile(filepath.Join(modsDir, "zzz_Test_P.utoc"), []byte("user"), 0o644); err != nil {
		t.Fatal(err)
	}
	err := Install(gameRoot, m, st, false)
	if err == nil {
		t.Fatal("应报占用")
	}
	if _, ok := err.(*OccupiedError); !ok {
		t.Fatalf("应是 OccupiedError，实际 %T: %v", err, err)
	}
	// force 覆盖
	if err := Install(gameRoot, m, st, true); err != nil {
		t.Fatalf("force 安装失败: %v", err)
	}
}

func TestRestoreAll(t *testing.T) {
	gameRoot, m := setup(t)
	st := LoadState()
	if err := Install(gameRoot, m, st, false); err != nil {
		t.Fatal(err)
	}
	if _, err := RestoreAll(gameRoot, st); err != nil {
		t.Fatalf("还原失败: %v", err)
	}
	if len(st.Installed) != 0 {
		t.Fatal("还原后状态应为空")
	}
	modsDir := discovery.ModsDir(gameRoot)
	if _, err := os.Stat(filepath.Join(modsDir, "zzz_Test_P.ucas")); !os.IsNotExist(err) {
		t.Fatal("文件未被删除")
	}
}

func TestInstallRejectsBadGameRoot(t *testing.T) {
	t.Setenv("LOCALAPPDATA", t.TempDir())
	st := LoadState()
	m := modrepo.Mod{ID: "x", Name: "x"}
	if err := Install(t.TempDir(), m, st, false); err == nil {
		t.Fatal("无效游戏目录应报错")
	}
}

func TestConfigRoundTrip(t *testing.T) {
	t.Setenv("LOCALAPPDATA", t.TempDir())
	c := &Config{GameRoot: `D:\Games\PBZ`, ModsRepo: `D:\PBZ\Mods`}
	if err := SaveConfig(c); err != nil {
		t.Fatal(err)
	}
	got := LoadConfig()
	if got.GameRoot != c.GameRoot || got.ModsRepo != c.ModsRepo {
		t.Fatalf("配置读写不一致: %+v", got)
	}
}
