package main

import (
	"strings"
	"testing"
)

func TestDisplayWidthCountsWideRunes(t *testing.T) {
	cases := []struct {
		in   string
		want int
	}{
		{"", 0},
		{"abc", 3},
		{"零（异环）替换魂", 16}, // 8 个全角字符
		{"1.0.0", 5},
		{"零1.0.0", 7},        // 全角 2 + 5 个 ASCII
		{"⚠ 缺少同名 .ucas", 16}, // ⚠ 按 1 列、空格 1、中文 5×2、其余 6
	}
	for _, c := range cases {
		if got := displayWidth(c.in); got != c.want {
			t.Errorf("displayWidth(%q) = %d, want %d", c.in, got, c.want)
		}
	}
}

func TestPadRightAndPadLeftProduceEqualWidth(t *testing.T) {
	left := padLeft("1.0.0", 12)
	right := padRight("零（异环）", 12) // 8 列内容 + 4 个空格
	if displayWidth(left) != 12 {
		t.Fatalf("padLeft width = %d, want 12", displayWidth(left))
	}
	if displayWidth(right) != 12 {
		t.Fatalf("padRight width = %d, want 12", displayWidth(right))
	}
	if !strings.HasPrefix(right, "零（异环）") {
		t.Fatalf("padRight must not move the leading content: %q", right)
	}
	if left[len(left)-1] != '0' {
		t.Fatalf("padLeft must keep content at the end: %q", left)
	}
	// 太长的内容按显示宽度截断，不能把整行顶歪
	if got := displayWidth(padRight("零（异环）替换魂", 12)); got != 12 {
		t.Fatalf("overlong padRight width = %d, want 12", got)
	}
}

func TestTruncDisplayNeverExceedsWidth(t *testing.T) {
	long := "零（异环）替换魂——这是一个很长的 mod 名称，用来验证截断"
	for _, w := range []int{4, 10, 20, 40} {
		got := truncDisplay(long, w)
		if dw := displayWidth(got); dw > w {
			t.Fatalf("truncDisplay(%d) width = %d, exceeds %d: %q", w, dw, w, got)
		}
	}
	// 短字符串原样返回（不加省略号）
	if got := truncDisplay("1.0.0", 10); got != "1.0.0" {
		t.Fatalf("short string changed: %q", got)
	}
}

func TestHumanSize(t *testing.T) {
	cases := []struct {
		in   int64
		want string
	}{
		{0, "0 B"},
		{1023, "1023 B"},
		{1024, "1.0 KB"},
		{68369712 + 17231 + 509, "65.2 MB"},
	}
	for _, c := range cases {
		if got := humanSize(c.in); got != c.want {
			t.Errorf("humanSize(%d) = %q, want %q", c.in, got, c.want)
		}
	}
}
