package ui

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/lxn/walk"
	. "github.com/lxn/walk/declarative"

	"pbzmodkit/internal/discovery"
	"pbzmodkit/internal/install"
	"pbzmodkit/internal/modrepo"
	"pbzmodkit/internal/winutil"
)

// Version 由构建脚本通过 -ldflags 注入。
var Version = "0.1.0"

// 列表列序号（与 MainWindow 里的 Columns 顺序一一对应）。
const (
	colName = iota
	colVersion
	colAuthor
	colSize
	colStatus
	colNote
	colCount
)

// App 保存界面控件与运行期状态。
type App struct {
	mw        *walk.MainWindow
	gameEdit  *walk.LineEdit
	statusLbl *walk.Label
	repoLbl   *walk.Label
	table     *walk.TableView
	logBox    *walk.TextEdit
	model     *modTableModel

	mods     []modrepo.Mod
	state    *install.State
	cfg      *install.Config
	modsRepo string
	gameRoot string
}

// Run 启动界面，阻塞到窗口关闭。
func Run() error {
	a := &App{
		state: install.LoadState(),
		cfg:   install.LoadConfig(),
	}
	exe, _ := os.Executable()
	a.modsRepo = a.cfg.ModsRepo
	if a.modsRepo == "" {
		a.modsRepo = discovery.DefaultModsRepo(exe)
	}
	if a.cfg.GameRoot != "" {
		if ok, _ := discovery.ValidateRoot(a.cfg.GameRoot); ok {
			a.gameRoot = a.cfg.GameRoot
		}
	}
	a.model = &modTableModel{}

	if err := (MainWindow{
		AssignTo: &a.mw,
		Title:    "PBZ Mod Kit v" + Version,
		Size:     Size{Width: 980, Height: 680},
		Layout:   VBox{},
		Children: []Widget{
			Label{Text: "游戏路径（可手动粘贴，改完点「应用」）:"},
			LineEdit{AssignTo: &a.gameEdit, Text: a.gameRoot},
			Composite{
				Layout: HBox{},
				Children: []Widget{
					PushButton{Text: "自动检测", OnClicked: a.onAutoDetect},
					PushButton{Text: "应用路径", OnClicked: a.onApplyPath},
					PushButton{Text: "打开游戏目录", OnClicked: a.onOpenGameDir},
					HSpacer{},
					PushButton{Text: "打开 Mods 目录", OnClicked: a.onOpenRepo},
				},
			},
			Label{AssignTo: &a.statusLbl, Text: "状态：未选择游戏目录"},
			Label{AssignTo: &a.repoLbl, Text: ""},
			TableView{
				AssignTo:                 &a.table,
				Model:                    a.model,
				MinSize:                  Size{Height: 280},
				AlternatingRowBG:         true,
				ColumnsSizable:           true,
				LastColumnStretched:      true,
				NotSortableByHeaderClick: true,
				// 选中行即"当前 mod"，卸载/安装都按它来。
				OnCurrentIndexChanged: a.onSelectionChanged,
				Columns: []TableViewColumn{
					// 固定宽度之和控制在窗口默认宽度之内，否则会出现横向滚动条；
					// 最后一列（说明）由 LastColumnStretched 填满剩余空间。
					{Title: "名称", Width: 260},
					{Title: "版本", Width: 96, Alignment: AlignFar},
					{Title: "作者", Width: 100},
					{Title: "大小", Width: 92, Alignment: AlignFar},
					{Title: "状态", Width: 76, Alignment: AlignCenter},
					{Title: "说明", Width: 220},
				},
			},
			Composite{
				Layout: HBox{},
				Children: []Widget{
					PushButton{Text: "安装选中", OnClicked: a.onInstall},
					PushButton{Text: "卸载选中", OnClicked: a.onUninstall},
					PushButton{Text: "全部还原", OnClicked: a.onRestoreAll},
					PushButton{Text: "刷新列表", OnClicked: a.onRefresh},
					PushButton{Text: "打开 ~mods", OnClicked: a.onOpenModsDir},
				},
			},
			Label{Text: "日志:"},
			TextEdit{
				AssignTo: &a.logBox,
				ReadOnly: true,
				VScroll:  true,
				MinSize:  Size{Height: 120},
			},
		},
	}).Create(); err != nil {
		return err
	}

	// TableView 默认允许横向滚动，这时 walk 的 StretchLastColumn 会退化成
	// "按表头宽度自适应"，最后一列不会填满剩余空间（窗口右侧留白）。
	// 关掉横向滚动后它走算术分支：末列宽 = 客户区宽 - 其余列宽之和。
	// 我们的列宽之和本来就小于窗口宽度，用不到横向滚动。
	a.table.SetScrollbarOrientation(walk.Vertical)

	a.logf("PBZ Mod Kit v%s 启动", Version)
	a.logf("Mods 仓库: %s", a.modsRepo)
	if a.gameRoot != "" {
		a.logf("已恢复上次的游戏目录: %s", a.gameRoot)
		a.updateStatus()
	} else {
		a.onAutoDetect()
	}
	a.refresh()
	a.mw.Run()
	return nil
}

// ---------- 列表模型 ----------
//
// 界面用 TableView（真表格，每列独立宽度/对齐），不再用 ListBox 拼空格字符串：
// 中文是等宽双字节、数字是单字节，空格填充在比例字体下永远对不齐。

type modRow struct {
	name    string
	version string
	author  string
	size    string
	status  string
	note    string
}

type modTableModel struct {
	walk.TableModelBase
	rows []modRow
}

func (m *modTableModel) RowCount() int { return len(m.rows) }

func (m *modTableModel) Value(row, col int) interface{} {
	if row < 0 || row >= len(m.rows) {
		return ""
	}
	r := m.rows[row]
	switch col {
	case colName:
		return r.name
	case colVersion:
		return r.version
	case colAuthor:
		return r.author
	case colSize:
		return r.size
	case colStatus:
		return r.status
	case colNote:
		return r.note
	}
	return ""
}

func (m *modTableModel) setRows(rows []modRow) {
	m.rows = rows
	m.PublishRowsReset()
}

// displayVersion / displayAuthor 保证每一行同一个字段要么有值、要么有占位符，
// 不会出现"空着"的单元格让列看起来错位。
func displayVersion(v string) string {
	v = strings.TrimSpace(v)
	if v == "" {
		return "—"
	}
	return v
}

func displayAuthor(v string) string {
	v = strings.TrimSpace(v)
	if v == "" {
		return "未署名"
	}
	return v
}

// ---------- 日志与状态 ----------

func (a *App) logf(format string, args ...interface{}) {
	line := fmt.Sprintf("[%s] %s\r\n", time.Now().Format("15:04:05"), fmt.Sprintf(format, args...))
	if a.logBox != nil {
		a.logBox.AppendText(line)
	}
	appendLogFile(strings.TrimRight(line, "\r\n"))
}

func appendLogFile(line string) {
	dir := filepath.Join(install.DataDir(), "logs")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return
	}
	f, err := os.OpenFile(filepath.Join(dir, "app-"+time.Now().Format("20060102")+".log"),
		os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		return
	}
	defer f.Close()
	_, _ = f.WriteString(line + "\r\n")
}

func (a *App) updateStatus() {
	if a.gameRoot == "" {
		a.statusLbl.SetText("状态：未选择游戏目录")
		return
	}
	ok, reason := discovery.ValidateRoot(a.gameRoot)
	if !ok {
		a.statusLbl.SetText("状态：目录无效 — " + reason)
		return
	}
	running := "未运行"
	if isGameRunning() {
		running = "⚠ 正在运行（请先退出）"
	}
	a.statusLbl.SetText(fmt.Sprintf("状态：✓ 已识别 · %d 个容器 · %s", discovery.CountUTOC(a.gameRoot), running))
}

// refresh 重新扫描仓库并刷新表格；尽量保留原来选中的那一行。
func (a *App) refresh() {
	a.repoLbl.SetText("Mod 列表（来源：" + a.modsRepo + "）：")
	if a.modsRepo == "" {
		a.mods = nil
		a.model.setRows([]modRow{{name: "（未设置 Mods 目录）"}})
		return
	}
	mods, err := modrepo.Scan(a.modsRepo)
	if err != nil {
		a.logf("扫描 Mods 目录失败: %v", err)
		a.mods = nil
		a.model.setRows([]modRow{{name: "（扫描失败：" + err.Error() + "）"}})
		return
	}
	keep := ""
	if m := a.currentMod(); m != nil {
		keep = m.ID
	}
	a.mods = mods
	rows := make([]modRow, 0, len(mods))
	for _, m := range mods {
		state := "未安装"
		if a.state.Find(m.ID) != nil {
			state = "已安装"
		}
		note := strings.TrimSpace(m.Description)
		if m.Problem != "" {
			note = "⚠ " + m.Problem
			state = "不可用"
		}
		rows = append(rows, modRow{
			name:    m.Name,
			version: displayVersion(m.Version),
			author:  displayAuthor(m.Author),
			size:    humanSize(m.TotalSize),
			status:  state,
			note:    note,
		})
	}
	if len(rows) == 0 {
		rows = append(rows, modRow{name: "（这个目录下还没有 mod）"})
	}
	a.model.setRows(rows)

	if keep != "" {
		for i, m := range a.mods {
			if m.ID == keep {
				_ = a.table.SetCurrentIndex(i)
				break
			}
		}
	}
	a.updateStatus()
}

func (a *App) onSelectionChanged() {
	m := a.currentMod()
	if m == nil {
		return
	}
	// 选中即把完整信息写进日志：表格里的说明列会被宽度截断，这里给全文。
	ver := displayVersion(m.Version)
	author := displayAuthor(m.Author)
	a.logf("选中: %s · v%s · 作者 %s · %s", m.Name, ver, author, humanSize(m.TotalSize))
	if m.Description != "" {
		a.logf("  说明: %s", m.Description)
	}
}

func (a *App) currentMod() *modrepo.Mod {
	if a.table == nil {
		return nil
	}
	i := a.table.CurrentIndex()
	if i < 0 || i >= len(a.mods) {
		return nil
	}
	return &a.mods[i]
}

// ---------- 事件 ----------

func (a *App) onAutoDetect() {
	a.logf("正在搜索 Steam / WeGame / 磁盘 ...")
	list := discovery.DiscoverAll()
	if len(list) == 0 {
		a.logf("没有自动找到游戏，请手动粘贴游戏根目录（含 ProjectPBZ\\Content\\Paks）")
		return
	}
	a.logf("找到 %d 个候选：", len(list))
	for _, g := range list {
		a.logf("  [%s] %s  buildid=%s  utoc=%d", g.Source, g.Root, emptyAs(g.BuildID, "-"), g.UTOC)
	}
	a.setGame(list[0].Root)
	a.refresh()
}

func (a *App) onApplyPath() {
	p := strings.TrimSpace(a.gameEdit.Text())
	if p == "" {
		a.logf("路径为空")
		return
	}
	a.setGame(p)
	a.refresh()
}

func (a *App) setGame(p string) {
	ok, reason := discovery.ValidateRoot(p)
	if !ok {
		a.logf("目录无效（%s）: %s", reason, p)
		a.statusLbl.SetText("状态：目录无效 — " + reason)
		walk.MsgBox(a.mw, "目录无效", reason+"\r\n\r\n请检查是否选到了游戏根目录：\r\n"+p, walk.MsgBoxIconWarning)
		return
	}
	a.gameRoot = filepath.Clean(p)
	a.gameEdit.SetText(a.gameRoot)
	a.cfg.GameRoot = a.gameRoot
	if err := install.SaveConfig(a.cfg); err != nil {
		a.logf("保存配置失败: %v", err)
	}
	a.logf("已选择游戏目录: %s", a.gameRoot)
	a.updateStatus()
}

func (a *App) onInstall() {
	m := a.currentMod()
	if m == nil {
		walk.MsgBox(a.mw, "提示", "请先在列表里选中一个 mod", walk.MsgBoxIconInformation)
		return
	}
	if a.gameRoot == "" {
		walk.MsgBox(a.mw, "提示", "请先设置游戏目录", walk.MsgBoxIconInformation)
		return
	}
	err := install.Install(a.gameRoot, *m, a.state, false)
	if err != nil {
		switch e := err.(type) {
		case *install.OccupiedError:
			if walk.MsgBox(a.mw, "文件已存在",
				"~mods 里已有这些文件（不是本工具装的）：\r\n"+strings.Join(e.Files, "\r\n")+"\r\n\r\n要覆盖吗？",
				walk.MsgBoxYesNo|walk.MsgBoxIconQuestion) == walk.DlgCmdYes {
				if err2 := install.Install(a.gameRoot, *m, a.state, true); err2 != nil {
					a.reportErr("安装失败", err2)
					return
				}
			} else {
				return
			}
		case *install.ConflictError:
			if walk.MsgBox(a.mw, "冲突",
				e.Error()+"\r\n\r\n要先卸载它再装这个吗？",
				walk.MsgBoxYesNo|walk.MsgBoxIconQuestion) == walk.DlgCmdYes {
				a.uninstallConflictAndRetry(e)
			}
			return
		default:
			a.reportErr("安装失败", err)
			return
		}
	}
	a.logf("已安装: %s", m.Name)
	a.refresh()
}

// uninstallConflictAndRetry 卸载冲突的旧 mod 后重装当前选中的 mod。
func (a *App) uninstallConflictAndRetry(e *install.ConflictError) {
	for _, ins := range a.state.Installed {
		if ins.Target == e.Target && ins.Name == e.Existing {
			if _, err := install.Uninstall(a.gameRoot, ins.ModID, a.state); err != nil {
				a.reportErr("卸载旧 mod 失败", err)
				return
			}
			a.logf("已卸载旧 mod: %s", ins.Name)
			break
		}
	}
	if m := a.currentMod(); m != nil {
		if err := install.Install(a.gameRoot, *m, a.state, false); err != nil {
			a.reportErr("安装失败", err)
			return
		}
		a.logf("已安装: %s", m.Name)
	}
	a.refresh()
}

func (a *App) onUninstall() {
	m := a.currentMod()
	if m == nil {
		walk.MsgBox(a.mw, "提示", "请先在列表里选中一个 mod", walk.MsgBoxIconInformation)
		return
	}
	if a.gameRoot == "" {
		walk.MsgBox(a.mw, "提示", "请先设置游戏目录", walk.MsgBoxIconInformation)
		return
	}
	if a.state.Find(m.ID) == nil {
		walk.MsgBox(a.mw, "提示", "这个 mod 当前没有安装", walk.MsgBoxIconInformation)
		return
	}
	warns, err := install.Uninstall(a.gameRoot, m.ID, a.state)
	for _, w := range warns {
		a.logf("警告: %s", w)
	}
	if err != nil {
		a.reportErr("卸载失败", err)
		return
	}
	a.logf("已卸载: %s", m.Name)
	a.refresh()
}

func (a *App) onRestoreAll() {
	if a.gameRoot == "" {
		walk.MsgBox(a.mw, "提示", "请先设置游戏目录", walk.MsgBoxIconInformation)
		return
	}
	if len(a.state.Installed) == 0 {
		walk.MsgBox(a.mw, "提示", "当前没有本工具安装的 mod", walk.MsgBoxIconInformation)
		return
	}
	if walk.MsgBox(a.mw, "确认", fmt.Sprintf("将移除本工具安装的 %d 个 mod，确定？", len(a.state.Installed)),
		walk.MsgBoxYesNo|walk.MsgBoxIconQuestion) != walk.DlgCmdYes {
		return
	}
	warns, err := install.RestoreAll(a.gameRoot, a.state)
	for _, w := range warns {
		a.logf("警告: %s", w)
	}
	if err != nil {
		a.reportErr("还原失败", err)
		return
	}
	a.logf("已全部还原")
	a.refresh()
}

func (a *App) onRefresh() {
	a.refresh()
	a.logf("已刷新（%d 个 mod）", len(a.mods))
}

func (a *App) onOpenGameDir() {
	if a.gameRoot == "" {
		return
	}
	openInExplorer(a.gameRoot)
}

func (a *App) onOpenModsDir() {
	if a.gameRoot == "" {
		walk.MsgBox(a.mw, "提示", "请先设置游戏目录", walk.MsgBoxIconInformation)
		return
	}
	dir := discovery.ModsDir(a.gameRoot)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		a.logf("创建 ~mods 失败: %v", err)
	}
	openInExplorer(dir)
}

func (a *App) onOpenRepo() {
	openInExplorer(a.modsRepo)
}

func (a *App) reportErr(title string, err error) {
	a.logf("%s: %v", title, err)
	walk.MsgBox(a.mw, title, err.Error(), walk.MsgBoxIconError)
}

// ---------- 小工具 ----------

func isGameRunning() bool { return winutil.IsProcessRunning("PBZ.exe") }

func openInExplorer(p string) {
	if p == "" {
		return
	}
	_ = exec.Command("explorer.exe", p).Start()
}

func humanSize(n int64) string {
	const unit = 1024
	if n < unit {
		return fmt.Sprintf("%d B", n)
	}
	div, exp := int64(unit), 0
	for v := n / unit; v >= unit; v /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(n)/float64(div), "KMGT"[exp])
}

func emptyAs(s, alt string) string {
	if strings.TrimSpace(s) == "" {
		return alt
	}
	return s
}
