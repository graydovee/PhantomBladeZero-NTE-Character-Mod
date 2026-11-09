package install

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"pbzmodkit/internal/discovery"
	"pbzmodkit/internal/modrepo"
	"pbzmodkit/internal/winutil"
)

// ErrGameRunning 表示游戏还在运行，不能改 ~mods。
var ErrGameRunning = errors.New("游戏正在运行（PBZ.exe），请先完全退出")

// gameRunning 是可替换的进程检测（单元测试里会替换成恒 false）。
var gameRunning = func() bool { return winutil.IsProcessRunning("PBZ.exe") }

// ConflictError 表示互斥分组冲突（例如两套主角替换 mod）。
type ConflictError struct {
	Target   string
	Existing string
}

func (e *ConflictError) Error() string {
	return fmt.Sprintf("与已安装的「%s」冲突（同属 %s 组），请先卸载它", e.Existing, e.Target)
}

// OccupiedError 表示 ~mods 里已有同名文件但不属于本工具。
type OccupiedError struct {
	Files []string
}

func (e *OccupiedError) Error() string {
	return "~mods 里已存在同名文件（不是本工具安装的）: " + strings.Join(e.Files, ", ")
}

// MissingGame 表示游戏目录不可用。
type MissingGame struct{ Reason string }

func (e *MissingGame) Error() string { return "游戏目录无效: " + e.Reason }

// Install 把 mod 的容器复制进 ~mods。force=true 时覆盖非本工具的同名文件。
func Install(gameRoot string, m modrepo.Mod, st *State, force bool) error {
	ok, reason := discovery.ValidateRoot(gameRoot)
	if !ok {
		return &MissingGame{Reason: reason}
	}
	if gameRunning() {
		return ErrGameRunning
	}
	if m.Problem != "" {
		return errors.New(m.Problem)
	}

	// 互斥分组检查（同 ID 视为替换，不算冲突）
	if m.Target != "" {
		for _, ins := range st.Installed {
			if ins.ModID != m.ID && ins.Target == m.Target {
				return &ConflictError{Target: m.Target, Existing: ins.Name}
			}
		}
	}

	modsDir := discovery.ModsDir(gameRoot)
	if err := os.MkdirAll(modsDir, 0o755); err != nil {
		return fmt.Errorf("创建 ~mods 失败（可能需要管理员权限）: %w", err)
	}

	names := m.ContainerFiles()
	if len(names) == 0 {
		return errors.New("这个 mod 没有可安装的容器文件")
	}

	// 源文件清单（名字 → 源路径）
	type srcFile struct{ name, src string }
	var srcs []srcFile
	for _, base := range m.Bases {
		for _, ext := range []string{".utoc", ".ucas", ".pak"} {
			p := base + ext
			if _, err := os.Stat(p); err == nil {
				srcs = append(srcs, srcFile{filepath.Base(base) + ext, p})
			}
		}
	}
	if len(srcs) == 0 {
		return errors.New("这个 mod 没有可安装的容器文件")
	}

	// 已存在文件的处理：
	//   内容与源文件一致      → 视为"记录丢失"，直接接管（不打扰用户）
	//   是本工具装过的旧版本  → 直接更新
	//   其它（内容不同且非本工具）→ 报占用，让用户确认
	var occupied []string
	for _, s := range srcs {
		dst := filepath.Join(modsDir, s.name)
		if _, err := os.Stat(dst); err != nil {
			continue
		}
		if same, _ := sameContent(dst, s.src); same {
			continue
		}
		if ownsFile(st, s.name) {
			continue
		}
		occupied = append(occupied, s.name)
	}
	if len(occupied) > 0 && !force {
		return &OccupiedError{Files: occupied}
	}

	rec := InstalledMod{
		ModID:       m.ID,
		Name:        m.Name,
		Target:      m.Target,
		SourceDir:   m.Dir,
		InstalledAt: time.Now(),
	}
	for _, s := range srcs {
		dst := filepath.Join(modsDir, s.name)
		// 已经在位且内容一致 → 只记录，不重复复制（省一次 130 MB 的写盘）
		if same, _ := sameContent(dst, s.src); same {
			sum, size, err := fileSHA256Size(dst)
			if err == nil {
				rec.Files = append(rec.Files, FileRec{Name: s.name, Size: size, SHA256: sum})
				continue
			}
		}
		sum, size, err := copyHashed(s.src, dst)
		if err != nil {
			return fmt.Errorf("复制 %s 失败: %w", s.name, err)
		}
		rec.Files = append(rec.Files, FileRec{Name: s.name, Size: size, SHA256: sum})
	}
	if len(rec.Files) == 0 {
		return errors.New("没有复制到任何文件")
	}

	// 同 ID 已安装 → 先移除旧记录（文件已被覆盖）
	filtered := st.Installed[:0]
	for _, ins := range st.Installed {
		if ins.ModID != m.ID {
			filtered = append(filtered, ins)
		}
	}
	st.Installed = append(filtered, rec)
	st.GameRoot = gameRoot
	return st.Save()
}

// Uninstall 删除某个 mod 已安装的文件。
func Uninstall(gameRoot, modID string, st *State) (warnings []string, err error) {
	if gameRunning() {
		return nil, ErrGameRunning
	}
	ins := st.Find(modID)
	if ins == nil {
		return nil, fmt.Errorf("没有找到已安装记录: %s", modID)
	}
	modsDir := discovery.ModsDir(gameRoot)
	for _, f := range ins.Files {
		p := filepath.Join(modsDir, f.Name)
		if _, statErr := os.Stat(p); statErr != nil {
			continue
		}
		if f.SHA256 != "" {
			if sum, _ := fileSHA256(p); sum != "" && sum != f.SHA256 {
				warnings = append(warnings, fmt.Sprintf("%s 内容已被改动，仍然删除", f.Name))
			}
		}
		if rmErr := os.Remove(p); rmErr != nil {
			return warnings, fmt.Errorf("删除 %s 失败: %w", f.Name, rmErr)
		}
	}
	filtered := st.Installed[:0]
	for _, ins2 := range st.Installed {
		if ins2.ModID != modID {
			filtered = append(filtered, ins2)
		}
	}
	st.Installed = filtered
	st.GameRoot = gameRoot
	return warnings, st.Save()
}

// RestoreAll 清空本工具安装的全部文件。
func RestoreAll(gameRoot string, st *State) (warnings []string, err error) {
	if gameRunning() {
		return nil, ErrGameRunning
	}
	modsDir := discovery.ModsDir(gameRoot)
	for _, ins := range st.Installed {
		for _, f := range ins.Files {
			p := filepath.Join(modsDir, f.Name)
			if _, statErr := os.Stat(p); statErr != nil {
				continue
			}
			if rmErr := os.Remove(p); rmErr != nil {
				warnings = append(warnings, fmt.Sprintf("删除 %s 失败: %v", f.Name, rmErr))
			}
		}
	}
	st.Installed = nil
	st.GameRoot = gameRoot
	return warnings, st.Save()
}

func ownsFile(st *State, name string) bool {
	for _, ins := range st.Installed {
		for _, f := range ins.Files {
			if strings.EqualFold(f.Name, name) {
				return true
			}
		}
	}
	return false
}

func copyHashed(src, dst string) (sum string, size int64, err error) {
	in, err := os.Open(src)
	if err != nil {
		return "", 0, err
	}
	defer in.Close()

	if err = os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return "", 0, err
	}
	tmp := dst + ".part"
	out, err := os.Create(tmp)
	if err != nil {
		return "", 0, err
	}
	h := sha256.New()
	n, copyErr := io.Copy(io.MultiWriter(out, h), in)
	closeErr := out.Close()
	if copyErr != nil {
		_ = os.Remove(tmp)
		return "", 0, copyErr
	}
	if closeErr != nil {
		_ = os.Remove(tmp)
		return "", 0, closeErr
	}
	if err = os.Rename(tmp, dst); err != nil {
		_ = os.Remove(tmp)
		return "", 0, err
	}
	return hex.EncodeToString(h.Sum(nil)), n, nil
}

func fileSHA256(p string) (string, error) {
	f, err := os.Open(p)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

// fileSHA256Size 返回某文件的 sha256 与大小。
func fileSHA256Size(p string) (string, int64, error) {
	f, err := os.Open(p)
	if err != nil {
		return "", 0, err
	}
	defer f.Close()
	h := sha256.New()
	n, err := io.Copy(h, f)
	if err != nil {
		return "", 0, err
	}
	return hex.EncodeToString(h.Sum(nil)), n, nil
}

// sameContent 快速判断两个文件是否一致（先比大小，再比哈希）。
func sameContent(a, b string) (bool, error) {
	sa, err := os.Stat(a)
	if err != nil {
		return false, err
	}
	sb, err := os.Stat(b)
	if err != nil {
		return false, err
	}
	if sa.Size() != sb.Size() {
		return false, nil
	}
	ha, err := fileSHA256(a)
	if err != nil {
		return false, err
	}
	hb, err := fileSHA256(b)
	if err != nil {
		return false, err
	}
	return ha == hb, nil
}
