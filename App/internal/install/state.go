package install

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// FileRec 记录一个已安装文件，用于卸载时精确删除。
type FileRec struct {
	Name   string `json:"name"`
	Size   int64  `json:"size"`
	SHA256 string `json:"sha256,omitempty"`
}

// InstalledMod 记录一个已安装的 mod。
type InstalledMod struct {
	ModID       string    `json:"mod_id"`
	Name        string    `json:"name"`
	Target      string    `json:"target,omitempty"`
	SourceDir   string    `json:"source_dir,omitempty"`
	Files       []FileRec `json:"files"`
	InstalledAt time.Time `json:"installed_at"`
}

// State 是工具的安装状态（只记录自己装过的东西）。
type State struct {
	GameRoot  string         `json:"game_root"`
	Installed []InstalledMod `json:"installed"`

	path string
}

// Config 是用户偏好。
type Config struct {
	GameRoot string `json:"game_root,omitempty"`
	ModsRepo string `json:"mods_repo,omitempty"`
}

// DataDir 返回 GUI 与 CLI 共用的数据目录。
// 优先取环境变量 PBZMODKIT_DATA_DIR，其次 exe 旁的 data、LOCALAPPDATA，最后临时目录；
// PBZMODKIT_DATA_DIR 指向的目录不可写时，继续按候选顺序往下找。
func DataDir() string {
	if d := strings.TrimSpace(os.Getenv("PBZMODKIT_DATA_DIR")); d != "" {
		if err := os.MkdirAll(d, 0o755); err == nil {
			return d
		}
	}
	cands := []string{}
	if exe, err := os.Executable(); err == nil {
		cands = append(cands, filepath.Join(filepath.Dir(exe), "data"))
	}
	if base := os.Getenv("LOCALAPPDATA"); base != "" {
		cands = append(cands, filepath.Join(base, "PBZModKit"))
	}
	cands = append(cands, filepath.Join(os.TempDir(), "PBZModKit"))
	for _, d := range cands {
		if err := os.MkdirAll(d, 0o755); err != nil {
			continue
		}
		probe := filepath.Join(d, ".wtest")
		if f, err := os.Create(probe); err == nil {
			f.Close()
			os.Remove(probe)
			return d
		}
	}
	return cands[len(cands)-1]
}
func statePath() string  { return filepath.Join(DataDir(), "state.json") }
func configPath() string { return filepath.Join(DataDir(), "config.json") }

// LoadState 读取状态；文件缺失或损坏时返回空状态（不报错）。
func LoadState() *State {
	st := &State{path: statePath()}
	b, err := os.ReadFile(st.path)
	if err != nil {
		return st
	}
	if err := json.Unmarshal(b, st); err != nil {
		return &State{path: statePath()}
	}
	return st
}

// Save 原子写状态。
func (s *State) Save() error {
	b, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}
	return atomicWrite(s.path, b)
}

// Find 按 modID 找已安装记录。
func (s *State) Find(modID string) *InstalledMod {
	for i := range s.Installed {
		if s.Installed[i].ModID == modID {
			return &s.Installed[i]
		}
	}
	return nil
}

// LoadConfig 读取配置。
func LoadConfig() *Config {
	c := &Config{}
	if b, err := os.ReadFile(configPath()); err == nil {
		_ = json.Unmarshal(b, c)
	}
	return c
}

// SaveConfig 写入配置。
func SaveConfig(c *Config) error {
	b, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return err
	}
	return atomicWrite(configPath(), b)
}

func atomicWrite(path string, data []byte) error {
	// 目标目录可能被外部清掉（或首次运行），写之前确保存在
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}
