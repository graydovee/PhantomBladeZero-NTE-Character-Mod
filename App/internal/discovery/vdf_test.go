package discovery

import "testing"

func TestParseLibraryPathsNewFormat(t *testing.T) {
	vdf := `"libraryfolders"
{
	"0"
	{
		"path"		"D:\\Program Files (x86)\\Steam"
		"label"		""
		"contentid"		"12345"
	}
	"1"
	{
		"path"		"E:\\SteamLibrary"
	}
}`
	got := ParseLibraryPaths(vdf)
	want := []string{`D:\Program Files (x86)\Steam`, `E:\SteamLibrary`}
	if len(got) != len(want) {
		t.Fatalf("数量不对: got %v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("第 %d 项: got %q want %q", i, got[i], want[i])
		}
	}
}

func TestParseLibraryPathsOldFormat(t *testing.T) {
	vdf := `"LibraryFolders"
{
	"TimeNextStatsReport"		"1234"
	"1"		"D:\\Games\\Steam"
	"2"		"E:\\SteamLib"
}`
	got := ParseLibraryPaths(vdf)
	if len(got) != 2 || got[0] != `D:\Games\Steam` || got[1] != `E:\SteamLib` {
		t.Fatalf("老格式解析失败: %v", got)
	}
}

func TestUnescapeVDF(t *testing.T) {
	if got := UnescapeVDF(`D:\\Steam\\apps`); got != `D:\Steam\apps` {
		t.Fatalf("转义失败: %q", got)
	}
}
