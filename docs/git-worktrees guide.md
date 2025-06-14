# Git Worktrees Guide

Git worktrees allow you to have multiple working directories associated with a single repository, enabling you to work on different branches simultaneously without the overhead of cloning or constant branch switching.

## What are Git Worktrees?

A git worktree is an additional working directory linked to the same repository. Each worktree can have a different branch checked out, allowing you to:
- Work on multiple features simultaneously
- Compare different branches side-by-side
- Run tests on one branch while developing on another
- Avoid stashing changes when switching contexts

## Setting Up Git Worktrees on Linux

### Basic Commands

```bash
# Add a new worktree for an existing branch
git worktree add ../project-feature feature-branch

# Add a new worktree and create a new branch
git worktree add -b new-feature ../project-new-feature

# Add a worktree for a specific commit
git worktree add ../project-hotfix abc1234

# List all worktrees
git worktree list

# Remove a worktree
git worktree remove ../project-feature
# or
git worktree prune  # removes worktrees that no longer exist on disk
```

### Directory Structure Example

```
~/projects/
├── my-app/                 # Main repository
├── my-app-feature/         # Worktree for feature branch
├── my-app-hotfix/          # Worktree for hotfix
└── my-app-experimental/    # Worktree for experimental work
```

### Best Practices for Setup

1. **Use descriptive directory names**: Include branch name or purpose
2. **Keep worktrees at the same directory level**: Easier to navigate and manage
3. **Use relative paths**: `../project-branch` instead of absolute paths
4. **Clean up regularly**: Remove unused worktrees with `git worktree remove`

## Optimizing for AI Agent Coding

### Advantages for AI Development

1. **Context Preservation**: Each worktree maintains its own working directory state
2. **Parallel Development**: AI can work on multiple features without losing context
3. **Safe Experimentation**: Try different approaches in separate worktrees
4. **Branch Comparison**: Easily compare implementations across branches

### Recommended Workflow

```bash
# Main development worktree
git worktree add ../rent-app-main main

# Feature development
git worktree add -b user-auth ../rent-app-auth

# Experimental changes
git worktree add -b perf-optimization ../rent-app-perf

# Bug fixes
git worktree add -b fix-payment-bug ../rent-app-bugfix
```

### AI Agent Best Practices

1. **Branch Naming**: Use descriptive names that indicate the AI's task
   ```bash
   git worktree add -b ai/refactor-database ../rent-app-db-refactor
   git worktree add -b ai/add-validation ../rent-app-validation
   ```

2. **Task Isolation**: Each significant task gets its own worktree
   - Prevents context switching overhead
   - Maintains clean working directories
   - Allows parallel task execution

3. **Environment Management**: Each worktree can have different configurations
   ```bash
   # In each worktree, set specific environment variables
   cd ../rent-app-testing
   export STAGE=test
   export ISLOCAL=true
   ```

4. **Testing Strategy**: Use separate worktrees for different test scenarios
   ```bash
   git worktree add -b test/integration ../rent-app-integration-tests
   git worktree add -b test/performance ../rent-app-perf-tests
   ```

### Managing Dependencies

For projects with package managers (like this project using `uv`):

```bash
# Each worktree needs its own environment
cd ../rent-app-feature
uv sync  # Install dependencies for this worktree

# Or use shared virtual environments
export UV_PROJECT_ENVIRONMENT=../shared-venv
```

## Advanced Usage

### Bare Repository Setup

For maximum efficiency, start with a bare repository:

```bash
# Clone as bare repository
git clone --bare https://github.com/user/repo.git repo.git
cd repo.git

# Create worktrees from bare repo
git worktree add ../repo-main main
git worktree add ../repo-dev develop
```

### Shared Configuration

Create a script to standardize worktree creation:

```bash
#!/bin/bash
# create-worktree.sh
BRANCH_NAME=$1
WORKTREE_PATH="../$(basename $(pwd))-$BRANCH_NAME"

git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH"
cd "$WORKTREE_PATH"
uv sync  # Install dependencies
echo "Worktree created at $WORKTREE_PATH"
```

## Cleanup and Maintenance

### Regular Maintenance Commands

```bash
# List all worktrees and their status
git worktree list -v

# Remove worktrees that no longer exist on disk
git worktree prune

# Remove a specific worktree
git worktree remove path/to/worktree

# Force remove (if worktree has uncommitted changes)
git worktree remove --force path/to/worktree
```

### Automated Cleanup Script

```bash
#!/bin/bash
# cleanup-worktrees.sh
echo "Cleaning up worktrees..."
git worktree prune
git branch -d $(git branch --merged | grep -v '\*\|main\|develop')
echo "Cleanup complete"
```

## Troubleshooting

### Common Issues

1. **"fatal: invalid reference"**: Branch doesn't exist
   ```bash
   git fetch origin  # Update remote references
   git worktree add -b new-branch ../project-new origin/existing-branch
   ```

2. **Permission denied**: Check file permissions
   ```bash
   chmod -R u+w path/to/worktree
   ```

3. **Disk space**: Worktrees share the same `.git` directory, so they're space-efficient

## References

- [Official Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
- [Git Worktree Tutorial](https://git-scm.com/book/en/v2/Git-Tools-Advanced-Merging)
- [Atlassian Git Worktree Guide](https://www.atlassian.com/git/tutorials/git-worktree)
- [GitHub Documentation on Git Worktrees](https://docs.github.com/en/get-started/using-git/git-worktree)
- [Pro Git Book - Git Worktrees](https://git-scm.com/book/en/v2/Appendix-C%3A-Git-Commands-Sharing-and-Updating-Projects#_git_worktree)

## Integration with Development Tools

### VS Code
Each worktree can be opened as a separate VS Code window, maintaining independent:
- Extensions settings
- Debug configurations  
- Terminal sessions

### IDEs and Editors
Most modern editors handle worktrees transparently, treating each as an independent project root.