# Brazil Build System

## Workspaces and Package Structure

Code is pulled into a brazil workspace (you're probably working out of one right now). To check if you're in a workspace, run:

```
brazil workspace show
```

### Directory Structure

When you run `brazil workspace show`, you'll see the workspace root directory. The key thing to understand is:

1. The workspace root contains a `src/` directory
2. Inside `src/` are individual packages (each is a separate git repository)
3. You must navigate into a specific package directory to build it:
   ```
   cd src/PackageName
   ```
4. Always check the README.md file in the package for any specific build instructions
5. Run build commands only from within the package directory, not from the workspace root

Remember: You must be inside the specific package directory (e.g., `/path/to/WorkspaceName/src/PackageName/`) to build that package. Running build commands from the workspace root will fail.

You pull one or more brazil packages into a workspace via `brazil workspace use -p <package name>`. The packages will appear in the src/ folder of the workspace root. Each package is its own git repo so when committing changes that span multiple packages, you will need to create a separate commit per package. DO NOT modify files outside of brazil packages since they're not under version control.

## Building Packages

After navigating to the package directory:

1. First, check for a README.md or similar documentation file for custom build instructions
2. If custom instructions exist, follow those specific build steps
3. If no custom instructions are found, use one of the standard Brazil build processes:

   **Option 1: `brazil-build-analyzer-skill`**
   
   **Option 2: Standard build with log redirection to manage verbose output:**
   brazil-build commands can take a long time to run and the output can be very large, so you MUST save brazil-build output to a temp file. You SHOULD then parse the temp file with tools like grep or tail.
   ```bash
   # Run build and show only the last 20 lines (most relevant for success/failure)
   brazil-build release > build.log 2>&1 && echo -e "\n\n=== BUILD SUMMARY (LAST 20 LINES) ===\n" && tail -n 20 build.log
   
   # For more targeted output, use grep to filter for specific patterns
   brazil-build release > build.log 2>&1 && grep -A 5 "ERROR\|FAILED\|PASSED" build.log
   
   # If build fails, examine logs incrementally
   tail -n 50 build.log  # First 50 lines
   tail -n 100 build.log | head -n 50  # Next 50 lines
   ```

This will compile, run static analysis tools, and unit tests. It doesn't matter what language the package is written in, you should always build the package to verify any changes you've made. Fix any problems causing build failures. Address the root cause instead of the symptoms.

Generated build artifacts are saved into the build/ folder (symlink) of the package. Anything in build/private is just used during the build and is not published to the official package build artifacts.

## Building Multiple Packages

If you want to build all packages in the workspace together, you can do so from the `src` directory using:
```
brazil-recursive-cmd -allPackages brazil-build release
```
This command will recursively build all packages in the workspace in topological order, respecting their dependencies. You can also:

- Build specific packages with `-p PackageName1 -p PackageName2`
- The command automatically determines the correct build order based on package dependencies

## Troubleshooting Build Issues

If the build ends in error:

1. Verify you're in the correct package directory (not the workspace root)
2. Check for CannotFindBuildDirectoryException or messages like "Couldn't find a build directory at"
3. Try building with the recursive command:
   ```
   brazil-recursive-cmd brazil-build release
   ```
4. Look for specific error messages and address them directly

## Package Dependencies

When adding new package dependencies to a Brazil package:

1. Always verify that the package exists before adding it to the Config file. You can check if a package exists by checking `https://code.amazon.com/packages/<package name>`
2. To find the correct package names and versions, use code search with specific filters, e.g., `path:Config <dependency name>`
3. Look at existing packages with similar functionality to find the right dependencies and versions.
4. After adding new dependencies to the Config file, you may encounter build errors about missing dependencies in the version set. To resolve this:
   ```
   brazil workspace merge --local
   ```
   This command resolves any missing dependencies and adds them to the local workspace. After this, `brazil-build release` should work.

5. If you see errors about dependencies not being in the version set, always try `brazil workspace sync --metadata` first, followed by `brazil workspace merge --local` if that doesn't fix the problem.

Exception case: If the package is using NpmPrettyMuch, e.g., CDK code packages use this, then dependencies usually just go in package.json like usual. To understand what package versions are available, you can search this internal website: https://npmpm.corp.amazon.com/pkg/<package name> Example: `https://npmpm.corp.amazon.com/pkg/@amzn/pipelines`

### Dependency Sources

To pull down the source code for a Brazil dependency, run:

```
brazil-path '[PackageName]pkg.src'
```

This will return a filesystem path containing the package sources. Note that
this invocation only works when run from a Brazil package whose `Config` file
declares a direct dependency on `PackageName`. To obtain the sources for a
transitive dependency, the major version must be spelled out using `@`:

```
brazil-path '[PackageName@MV]pkg.src'
```
