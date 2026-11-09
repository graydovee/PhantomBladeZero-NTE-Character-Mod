package install

import (
	"os"
	"path/filepath"
	"testing"

	"pbzmodkit/internal/discovery"
)

// TestMain 关掉"游戏正在运行"的进程检测，让测试不受本机是否开着游戏影响。
func TestMain(m *testing.M) {
	gameRunning = func() bool { return false }
	os.Exit(m.Run())
}

// 回归测试：~mods 里的文件内容与 mod 源文件一致、但本地没有安装记录时，
// 应该"接管"（写入状态）而不是报"文件已存在"。
func TestInstallAdoptsIdenticalFilesWhenStateLost(t *testing.T) {
	gameRoot, m := setup(t)
	modsDir := discovery.ModsDir(gameRoot)

	// 模拟"已经手工复制进 ~mods"，但程序没有记录
	if err := os.MkdirAll(modsDir, 0o755); err != nil {
		t.Fatal(err)
	}
	for _, base := range m.Bases {
		for _, ext := range []string{".utoc", ".ucas"} {
			src := base + ext
			data, err := os.ReadFile(src)
			if err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(filepath.Join(modsDir, filepath.Base(base)+ext), data, 0o644); err != nil {
				t.Fatal(err)
			}
		}
	}

	st := LoadState() // 空状态（记录丢失）
	if err := Install(gameRoot, m, st, false); err != nil {
		t.Fatalf("内容一致时不应报占用，实际: %v", err)
	}
	if st.Find("zzz_Test_P") == nil {
		t.Fatal("应写入安装记录（接管）")
	}
	for _, f := range st.Find("zzz_Test_P").Files {
		if f.SHA256 == "" || f.Size == 0 {
			t.Fatalf("接管时也要记录哈希/大小: %+v", f)
		}
	}
}

// 内容不同且非本工具安装 → 仍然要报占用（避免误覆盖别人的 mod）。
func TestInstallStillRejectsDifferentForeignFile(t *testing.T) {
	gameRoot, m := setup(t)
	modsDir := discovery.ModsDir(gameRoot)
	if err := os.MkdirAll(modsDir, 0o755); err != nil {
		t.Fatal(err)
	}
	// 同名但内容不同、大小也不同
	if err := os.WriteFile(filepath.Join(modsDir, "zzz_Test_P.utoc"), []byte("someone-else"), 0o644); err != nil {
		t.Fatal(err)
	}
	st := LoadState()
	err := Install(gameRoot, m, st, false)
	if err == nil {
		t.Fatal("应报占用")
	}
	if _, ok := err.(*OccupiedError); !ok {
		t.Fatalf("应是 OccupiedError，实际 %T: %v", err, err)
	}
}
