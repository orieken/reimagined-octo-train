package main

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
)

func filterArgs(args []string) []string {
	cleanedArgs := make([]string, 0, len(args))
	for _, arg := range args {
		if arg != "-a" {
			cleanedArgs = append(cleanedArgs, arg)
		}
	}
	return cleanedArgs
}


func main() {
	args := os.Args[1:]

	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "❌ No command specified to run under Xvfb")
		os.Exit(1)
	}

	// Remove the -a flag if present
	cleanedArgs := filterArgs(args)

	if len(cleanedArgs) == 0 {
		fmt.Fprintln(os.Stderr, "❌ No valid command after removing flags")
		os.Exit(1)
	}

	// Start Xvfb on display :99
	display := ":99"
	xvfbCmd := exec.Command("Xvfb", display, "-screen", "0", "1280x1024x24")
	xvfbCmd.Stdout = os.Stdout
	xvfbCmd.Stderr = os.Stderr

	fmt.Println("🎬 Starting Xvfb on", display)
	if err := xvfbCmd.Start(); err != nil {
		fmt.Fprintln(os.Stderr, "❌ Failed to start Xvfb:", err)
		os.Exit(1)
	}
	defer xvfbCmd.Process.Kill()

	// Prepare the command to run
	fmt.Println("🚀 Running command:", strings.Join(cleanedArgs, " "))
	cmd := exec.Command(cleanedArgs[0], cleanedArgs[1:]...)
	cmd.Env = append(os.Environ(), "DISPLAY="+display)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	if err := cmd.Run(); err != nil {
		fmt.Fprintln(os.Stderr, "❌ Command failed:", err)
		os.Exit(1)
	}
}
