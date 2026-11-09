//go:build windows

package main

import (
	"os"
	"syscall"
)

const (
	attachParentProcess = ^uintptr(0) // (DWORD)-1
	fileTypeChar        = 0x0002      // FILE_TYPE_CHAR：控制台
)

// attachConsole 把输出接回父控制台：GUI 启动的子进程默认没有控制台，
// 从资源管理器双击时也看不到输出，这里重新挂上以便观察日志。
func attachConsole() {
	out := syscall.Stdout

	k := syscall.NewLazyDLL("kernel32.dll")
	attach := k.NewProc("AttachConsole")
	if r, _, _ := attach.Call(attachParentProcess); r == 0 {
		return // 没有父控制台，保持继承来的句柄（可能是管道/文件）
	}

	if t, err := syscall.GetFileType(out); err == nil && t != fileTypeChar {
		return // 已重定向到文件/管道，原样保留
	}

	if f, err := os.OpenFile("CONOUT$", os.O_WRONLY, 0); err == nil {
		os.Stdout = f
		os.Stderr = f
	}
}
