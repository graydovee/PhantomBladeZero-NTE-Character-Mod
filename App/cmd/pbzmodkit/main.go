package main

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"

	"pbzmodkit/internal/install"
	"pbzmodkit/internal/ui"
)

func main() {
	// 带参数 = 命令行模式（不启动 GUI），这样同一个 exe 既能双击开界面，
	// 也能在终端里 install/uninstall/switch，保证卸载与切换都走工具的记录。
	if len(os.Args) > 1 {
		attachConsole()
		os.Exit(runCLI(os.Args[1:]))
	}

	// walk 要求 UI 固定在主线程
	runtime.LockOSThread()

	if err := ui.Run(); err != nil {
		// windowsgui 模式没有控制台，错误写文件
		dir := filepath.Join(install.DataDir(), "logs")
		_ = os.MkdirAll(dir, 0o755)
		if f, ferr := os.Create(filepath.Join(dir, "startup-error.log")); ferr == nil {
			_, _ = fmt.Fprintf(f, "启动失败: %v\n", err)
			_ = f.Close()
		}
	}
}
