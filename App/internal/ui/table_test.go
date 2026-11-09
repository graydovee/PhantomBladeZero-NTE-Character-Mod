package ui

import "testing"

func TestModTableModelValueMapsEveryColumn(t *testing.T) {
	m := &modTableModel{}
	m.setRows([]modRow{{
		name:    "零（异环）替换魂",
		version: "1.0.0",
		author:  "示例作者",
		size:    "65.3 MB",
		status:  "已安装",
		note:    "原生骨架替换",
	}})

	if got := m.RowCount(); got != 1 {
		t.Fatalf("RowCount = %d, want 1", got)
	}
	want := []string{"零（异环）替换魂", "1.0.0", "示例作者", "65.3 MB", "已安装", "原生骨架替换"}
	for col, w := range want {
		if got := m.Value(0, col); got != w {
			t.Errorf("Value(0, %d) = %v, want %q", col, got, w)
		}
	}
	// 越界不能 panic，表格刷新瞬间会问到旧行号
	if got := m.Value(5, colName); got != "" {
		t.Errorf("out-of-range row should be empty, got %v", got)
	}
	if got := m.Value(0, colCount); got != "" {
		t.Errorf("out-of-range col should be empty, got %v", got)
	}
}

func TestDisplayFallbacks(t *testing.T) {
	if got := displayVersion("   "); got != "—" {
		t.Errorf("blank version should render placeholder, got %q", got)
	}
	if got := displayAuthor(""); got != "未署名" {
		t.Errorf("blank author should render 未署名, got %q", got)
	}
	if got := displayAuthor(" Hcxmmx "); got != "Hcxmmx" {
		t.Errorf("author should be trimmed, got %q", got)
	}
}
