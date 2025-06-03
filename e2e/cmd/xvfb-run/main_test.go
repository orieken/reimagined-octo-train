 package main

 import (
 	"os"
 	"os/exec"
 	"path/filepath"
 	"strings"
 	"testing"
 )

 func TestFilterArgsWithOnlyDashA(t *testing.T) {
 	args := []string{"-a"}
 	expected := []string{}

 	cleaned := filterArgs(args)

 	if len(cleaned) != len(expected) {
 		t.Fatalf("expected %d args, got %d", len(expected), len(cleaned))
 	}
 }

 func TestRemovesDashAFlag(t *testing.T) {
 	args := []string{"-a", "echo", "Hello"}
 	expected := []string{"echo", "Hello"}

 	cleaned := filterArgs(args)

 	if len(cleaned) != len(expected) {
 		t.Fatalf("expected %d args, got %d", len(expected), len(cleaned))
 	}
 	for i, v := range expected {
 		if cleaned[i] != v {
 			t.Errorf("expected %s at position %d, got %s", v, i, cleaned[i])
 		}
 	}
 }

 func TestNoCommandProvided(t *testing.T) {
 	cmd := exec.Command("go", "run", "main.go")
 	output, err := cmd.CombinedOutput()

 	if err == nil {
 		t.Fatal("expected an error when no command is provided")
 	}
 	if !strings.Contains(string(output), "No command specified") {
 		t.Errorf("expected error about missing command, got: %s", string(output))
 	}
 }

 func TestOnlyDashAProvided(t *testing.T) {
 	cmd := exec.Command("go", "run", "main.go", "-a")
 	output, err := cmd.CombinedOutput()

 	if err == nil {
 		t.Fatal("expected an error when only -a flag is provided")
 	}
 	if !strings.Contains(string(output), "No valid command after removing flags") {
 		t.Errorf("expected error about no valid command, got: %s", string(output))
 	}
 }

 func TestMultipleDashAFlags(t *testing.T) {
 	args := []string{"-a", "echo", "-a", "Hello", "-a"}
 	expected := []string{"echo", "Hello"}

 	cleaned := filterArgs(args)

 	if len(cleaned) != len(expected) {
 		t.Fatalf("expected %d args, got %d", len(expected), len(cleaned))
 	}
 	for i, v := range expected {
 		if cleaned[i] != v {
 			t.Errorf("expected %s at position %d, got %s", v, i, cleaned[i])
 		}
 	}
 }

 func TestCommandExecutionWithArgs(t *testing.T) {
 	// Skip this test if we're running in a CI environment without X
 	if os.Getenv("CI") != "" {
 		t.Skip("Skipping test in CI environment")
 	}

 	// Create a temporary helper program
 	helperDir := t.TempDir()
 	helperSrc := filepath.Join(helperDir, "helper.go")
 	helperBin := filepath.Join(helperDir, "helper")

 	// Write the helper program source
 	helperCode := `package main

 import (
 	"fmt"
 	"os"
 	"strings"
 )

 func main() {
 	display := os.Getenv("DISPLAY")
 	fmt.Printf("DISPLAY=%s\n", display)

 	if len(os.Args) > 1 {
 		fmt.Printf("ARGS=%s\n", strings.Join(os.Args[1:], " "))
 	} else {
 		fmt.Println("ARGS=")
 	}
 }
 `
 	if err := os.WriteFile(helperSrc, []byte(helperCode), 0644); err != nil {
 		t.Fatalf("Failed to write helper source: %v", err)
 	}

 	// Compile the helper
 	buildCmd := exec.Command("go", "build", "-o", helperBin, helperSrc)
 	if err := buildCmd.Run(); err != nil {
 		t.Fatalf("Failed to build helper: %v", err)
 	}

 	// Run the main program with the test helper
 	cmd := exec.Command("go", "run", "main.go", helperBin, "arg1", "arg2")
 	output, err := cmd.CombinedOutput()
 	outputStr := string(output)

 	// The main program might exit with an error if Xvfb is not available,
 	// but we can still check if it tried to set the DISPLAY variable
 	if !strings.Contains(outputStr, "Starting Xvfb on :99") {
 		t.Errorf("Expected to start Xvfb, got: %s", outputStr)
 	}

 	// If the test helper ran successfully, check its output
 	if err == nil && strings.Contains(outputStr, "DISPLAY=:99") {
 		// Check that arguments were passed correctly
 		if !strings.Contains(outputStr, "ARGS=arg1 arg2") {
 			t.Errorf("Arguments not passed correctly, got: %s", outputStr)
 		}
 	} else {
 		t.Logf("Test helper didn't run or Xvfb not available: %v\nOutput: %s", err, outputStr)
 	}
 }

 func TestNonExistentCommand(t *testing.T) {
 	// Run the main program with a non-existent command
 	cmd := exec.Command("go", "run", "main.go", "non_existent_command")
 	output, err := cmd.CombinedOutput()
 	outputStr := string(output)

 	// The program should try to start Xvfb
 	if !strings.Contains(outputStr, "Starting Xvfb on :99") {
 		t.Errorf("Expected to start Xvfb, got: %s", outputStr)
 	}

 	// The program should exit with an error when the command fails
 	if err == nil {
 		t.Fatal("Expected an error when command doesn't exist")
 	}

 	// Check for the error message - either Xvfb failed to start or the command failed
 	if !strings.Contains(outputStr, "Command failed") && !strings.Contains(outputStr, "Failed to start Xvfb") {
 		t.Errorf("Expected error about command failing or Xvfb failing, got: %s", outputStr)
 	}
 }
