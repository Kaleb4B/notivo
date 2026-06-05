#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <libgen.h>
#include <string.h>
#include <mach-o/dyld.h>
#include <limits.h>

void log_message(const char *msg) {
    FILE *f = fopen("/tmp/notivo_launcher.log", "a");
    if (f) {
        fprintf(f, "%s\n", msg);
        fclose(f);
    }
}

int main(int argc, char *argv[]) {
    log_message("--- Launcher started ---");
    
    // Attempt to cd to the absolute path of the project first
    const char *project_dir = "/Applications/MAMP/htdocs/Notivo";
    if (chdir(project_dir) == 0) {
        log_message("Changed directory to absolute project path: /Applications/MAMP/htdocs/Notivo");
    } else {
        log_message("Failed to cd to absolute project path. Trying relative path...");
        char path[PATH_MAX];
        uint32_t size = sizeof(path);
        if (_NSGetExecutablePath(path, &size) == 0) {
            char *dir = dirname(path);
            char app_dir[PATH_MAX];
            snprintf(app_dir, sizeof(app_dir), "%s/../../..", dir);
            if (chdir(app_dir) == 0) {
                char log_buf[2048];
                snprintf(log_buf, sizeof(log_buf), "Changed directory to relative path: %s", app_dir);
                log_message(log_buf);
            } else {
                log_message("Failed to change directory to relative path!");
            }
        } else {
            log_message("Failed to get executable path!");
        }
    }
    
    // Log active path and python execution
    char cwd[PATH_MAX];
    if (getcwd(cwd, sizeof(cwd)) != NULL) {
        char log_buf[2048];
        snprintf(log_buf, sizeof(log_buf), "Current working directory: %s", cwd);
        log_message(log_buf);
    }
    
    // Search for python3
    const char *python_paths[] = {
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/usr/bin/python3"
    };
    
    const char *selected_python = "python3"; // Fallback to PATH search
    for (int i = 0; i < 3; i++) {
        if (access(python_paths[i], X_OK) == 0) {
            selected_python = python_paths[i];
            break;
        }
    }
    
    char log_buf[2048];
    snprintf(log_buf, sizeof(log_buf), "Selected python executable: %s", selected_python);
    log_message(log_buf);
    
    char *args[] = {(char *)selected_python, "bootstrap.py", NULL};
    execvp(selected_python, args);
    
    // If execvp fails
    snprintf(log_buf, sizeof(log_buf), "execvp failed to launch %s with app.py", selected_python);
    log_message(log_buf);
    perror("Failed to launch Notivo");
    return 1;
}
