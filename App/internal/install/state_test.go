package install

import (
	"os"
	"path/filepath"
	"testing"
)

// 回归测试：数据目录不存在时（例如被用户清掉），写配置/状态要能自己建目录。
func TestSaveConfigCreatesMissingDataDir(t *testing.T) {
	base := t.TempDir()
	// 数据目录指向一个还不存在的多级目录（DataDir 会自己建）
	missing := filepath.Join(base, "not", "yet", "created")
	t.Setenv("PBZMODKIT_DATA_DIR", missing)

	c := &Config{GameRoot: `D:\Games\PBZ`, ModsRepo: `D:\PBZ\Mods`}
	if err := SaveConfig(c); err != nil {
		t.Fatalf("配置写入失败: %v", err)
	}
	if _, err := os.Stat(filepath.Join(missing, "config.json")); err != nil {
		t.Fatalf("配置文件没生成: %v", err)
	}
	got := LoadConfig()
	if got.GameRoot != c.GameRoot {
		t.Fatalf("读回不一致: %+v", got)
	}
}

func TestStateSaveCreatesMissingDataDir(t *testing.T) {
	base := t.TempDir()
	fresh := filepath.Join(base, "fresh")
	t.Setenv("PBZMODKIT_DATA_DIR", fresh)
	st := LoadState()
	st.GameRoot = `D:\x`
	if err := st.Save(); err != nil {
		t.Fatalf("状态写入失败: %v", err)
	}
	if _, err := os.Stat(filepath.Join(fresh, "state.json")); err != nil {
		t.Fatalf("state.json 没生成: %v", err)
	}
}
