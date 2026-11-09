package winutil

import (
	"strings"
	"unsafe"

	"golang.org/x/sys/windows"
)

// IsProcessRunning 判断指定 exe 名（含扩展名，如 PBZ.exe）是否在运行。
func IsProcessRunning(exeName string) bool {
	snap, err := windows.CreateToolhelp32Snapshot(windows.TH32CS_SNAPPROCESS, 0)
	if err != nil {
		return false
	}
	defer windows.CloseHandle(snap)

	var pe windows.ProcessEntry32
	pe.Size = uint32(unsafe.Sizeof(pe))
	if err := windows.Process32First(snap, &pe); err != nil {
		return false
	}
	want := strings.ToLower(strings.TrimSpace(exeName))
	for {
		name := strings.ToLower(windows.UTF16ToString(pe.ExeFile[:]))
		if name == want {
			return true
		}
		if err := windows.Process32Next(snap, &pe); err != nil {
			break
		}
	}
	return false
}
