# Blender bpy API Highlighting and IntelliSense Analysis

## Problem Statement

Blender API (`bpy`) highlighting and completion works correctly in the project `D:\ProgramData\telepass-blender` but does not work in the current project `modai-motion-capture-chain\modai`.

## Solution Summary: What Was Done to Enable Autocompletion, Suggestions, and Highlighting

### Assumption: Why It Works

The solution enables bpy IntelliSense and highlighting by configuring **three complementary systems** that Cursor uses for Python code analysis:

1. **cursorpyright Language Server** (Primary for Cursor)
2. **Pyright Configuration File** (Fallback/Standard)
3. **Semantic Highlighting System** (Visual feedback)

### Step-by-Step Changes Made

#### 1. Configured cursorpyright Language Server (`.vscode/settings.json`)

**Added:**
```json
{
  "python.languageServer": "None",           // Use Cursor's built-in cursorpyright
  "python.jediEnabled": false,                // Disable Jedi (limited support)
  "cursorpyright.analysis.extrapaths": [     // CRITICAL: Paths cursorpyright reads
    "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
  ],
  "cursorpyright.analysis.typeCheckingMode": "basic",
  "cursorpyright.analysis.autoImportCompletions": true,
  "cursorpyright.analysis.indexing": true
}
```

**Why this works:**
- `python.languageServer: "None"` tells Cursor to use its built-in cursorpyright instead of Pylance/Jedi
- `cursorpyright.analysis.extrapaths` is the **key setting** - this is what cursorpyright actually reads (not `python.analysis.extraPaths`)
- `indexing: true` allows cursorpyright to scan and index the bpy modules for autocompletion
- `autoImportCompletions: true` enables import suggestions

#### 2. Created Pyright Configuration File (`pyrightconfig.json`)

**Created:**
```json
{
  "pythonVersion": "3.11",
  "typeCheckingMode": "basic",
  "useLibraryCodeForTypes": true,
  "extraPaths": [
    "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
  ],
  "executionEnvironments": [
    {
      "root": ".",
      "extraPaths": [
        "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
      ]
    }
  ]
}
```

**Why this works:**
- Pyright-based language servers (including cursorpyright) read `pyrightconfig.json` as a standard configuration
- `extraPaths` tells Pyright where to find type stubs/modules
- `executionEnvironments` provides explicit environment configuration (more reliable than root-level paths)
- Acts as a fallback if workspace settings aren't read correctly

#### 3. Enabled Semantic Highlighting (`.vscode/settings.json`)

**Added:**
```json
{
  "editor.semanticHighlighting.enabled": true,
  "editor.semanticTokenColorCustomizations": {
    "enabled": true,
    "rules": {
      "namespace": "#4EC9B0",    // Color for modules/namespaces like 'bpy'
      "module": "#4EC9B0",
      "class": "#4EC9B0",
      "function": "#DCDCAA",
      "variable": "#9CDCFE"
    }
  },
  "editor.tokenColorCustomizations": {
    "textMateRules": [
      {
        "scope": [
          "entity.name.type.module.python",      // TextMate scope for Python modules
          "entity.name.namespace.python"
        ],
        "settings": {
          "foreground": "#4EC9B0"                // Cyan color for module names
        }
      }
    ]
  }
}
```

**Why this works:**
- `editor.semanticHighlighting.enabled: true` enables semantic token analysis from the language server
- `semanticTokenColorCustomizations` applies colors based on semantic token types (namespace, module, etc.)
- `tokenColorCustomizations.textMateRules` provides **fallback highlighting** using TextMate scopes when semantic tokens aren't available
- The language server recognizes `bpy` as a `namespace` or `module` token type, which gets colored cyan (#4EC9B0)

### How the Systems Work Together

```
┌─────────────────────────────────────────────────────────────┐
│ User types: import bpy                                      │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. cursorpyright Language Server                            │
│    - Reads cursorpyright.analysis.extrapaths                │
│    - Indexes bpy modules from fake_bpy_modules              │
│    - Provides: Autocompletion, type hints, semantic tokens  │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Pyright Config (pyrightconfig.json)                      │
│    - Fallback path resolution                               │
│    - Standard Pyright configuration                         │
│    - Ensures paths are found even if settings.json fails   │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Semantic Highlighting System                             │
│    - Receives semantic tokens from language server          │
│    - Applies colors based on token type (namespace/module)  │
│    - Falls back to TextMate rules if semantic tokens fail   │
│    - Result: bpy appears in cyan (#4EC9B0)                  │
└─────────────────────────────────────────────────────────────┘
```

### Key Insights

1. **cursorpyright vs Pylance**: Cursor uses cursorpyright, which reads `cursorpyright.analysis.extrapaths` (lowercase), NOT `python.analysis.extraPaths` (which is for Pylance/VS Code)

2. **Three-Layer Approach**:
   - Language server configuration (cursorpyright settings)
   - Standard config file (pyrightconfig.json)
   - Visual highlighting (semantic + TextMate rules)

   This redundancy ensures it works even if one layer fails.

3. **Path Resolution**: The fake_bpy_modules directory contains type stubs (`.pyi` files) that provide type information without requiring Blender to be running.

4. **Semantic Tokens**: The language server analyzes code and sends semantic token information (e.g., "this is a namespace") which the editor uses for highlighting, separate from syntax highlighting.

### Why User Settings Alone Didn't Work

Initially, only user-level settings were configured, but:
- User settings pointed to `telepass-blender` project-specific paths
- Workspace settings didn't have cursorpyright configuration
- No `pyrightconfig.json` file existed
- Semantic highlighting wasn't enabled

**Solution**: Added workspace-level configuration that:
- Overrides user settings for this project
- Provides project-specific paths
- Enables all three systems (language server, config file, highlighting)

## Root Cause Analysis

### Key Finding: Cursor Uses cursorpyright, Not Pylance

Cursor IDE uses its own built-in language server called **cursorpyright** (based on Pyright), which is different from VS Code's Pylance. The critical difference is:

- **VS Code/Pylance** reads: `python.analysis.extraPaths` and `python.analysis.stubPath`
- **Cursor/cursorpyright** reads: `cursorpyright.analysis.extrapaths` (note: lowercase "extrapaths")

### Current Configuration Comparison

#### Working Project (`telepass-blender`)

**Cursor User Settings** (`%USERPROFILE%\.cursor\User\settings.json`):
```json
{
    "python.languageServer": "None",
    "python.jediEnabled": false,
    "cursorpyright.analysis.extrapaths": [
        "D:/ProgramData/telepass-blender/venv/Lib/site-packages",
        "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
    ],
    "cursorpyright.analysis.typeCheckingMode": "basic",
    "cursorpyright.analysis.autoImportCompletions": true,
    "cursorpyright.analysis.indexing": true
}
```

**Workspace Settings** (`.vscode/settings.json`):
```json
{
    "python.languageServer": "None",
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.extraPaths": [
        "D:/ProgramData/telepass-blender/venv/Lib/site-packages",
        "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
    ],
    "python.analysis.stubPath": "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117",
    "python.analysis.autoImportCompletions": true,
    "python.analysis.diagnosticMode": "workspace",
    "python.analysis.indexing": true,
    "editor.semanticHighlighting.enabled": true,
    ...
}
```

**Pyright Configuration** (`pyrightconfig.json`):
```json
{
  "pythonVersion": "3.12",
  "typeCheckingMode": "basic",
  "useLibraryCodeForTypes": true,
  "extraPaths": [
    "D:/ProgramData/telepass-blender/venv/Lib/site-packages",
    "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
  ],
  "executionEnvironments": [
    {
      "root": ".",
      "extraPaths": [
        "D:/ProgramData/telepass-blender/venv/Lib/site-packages",
        "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
      ]
    }
  ]
}
```

#### Current Project (`modai-motion-capture-chain\modai`)

**Workspace Settings** (`.vscode/settings.json`):
```json
{
  "python.analysis.typeCheckingMode": "off",
  "python.analysis.extraPaths": [
      "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
  ],
  "python.analysis.stubPath": "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117",
  ...
}
```

**Missing Configuration:**
- ❌ No `cursorpyright.analysis.extrapaths` in workspace settings
- ❌ No `pyrightconfig.json` file
- ❌ No `python.languageServer` setting (defaults may conflict)
- ❌ No semantic highlighting configuration
- ❌ Cursor user settings point to telepass-blender paths (not this project)

### Why It Doesn't Work

1. **Cursor user settings are global** and point to `telepass-blender` paths, which don't apply to this project
2. **Workspace settings only have `python.analysis.extraPaths`**, which cursorpyright doesn't read
3. **No `cursorpyright.analysis.extrapaths`** configured in workspace settings
4. **No `pyrightconfig.json`** file for Pyright-based language servers to read
5. **Language server setting** may be conflicting (not explicitly set to "None")

### How Cursor Resolves Settings

Cursor reads settings in this priority order:
1. **Cursor User Settings** (`%USERPROFILE%\.cursor\User\settings.json`) - Global, applies to all projects
2. **Workspace Settings** (`.vscode/settings.json`) - Project-specific, can override user settings

For cursorpyright specifically:
- It reads `cursorpyright.analysis.extrapaths` from either location
- It also reads `pyrightconfig.json` if present in the project root
- It does NOT read `python.analysis.extraPaths` (that's for Pylance)

## Solution

### Option 1: Add cursorpyright Settings to Workspace (Recommended)

Add cursorpyright-specific settings to `.vscode/settings.json`:

```json
{
  "python.languageServer": "None",
  "python.jediEnabled": false,
  "cursorpyright.analysis.extrapaths": [
    "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
  ],
  "cursorpyright.analysis.typeCheckingMode": "basic",
  "cursorpyright.analysis.autoImportCompletions": true,
  "cursorpyright.analysis.indexing": true,
  "python.analysis.typeCheckingMode": "off",
  "python.analysis.extraPaths": [
    "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
  ],
  "python.analysis.stubPath": "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117",
  ...
}
```

**Benefits:**
- Works immediately for Cursor
- Doesn't affect global user settings
- Project-specific configuration
- Can still work with VS Code (uses `python.analysis.*` settings)

### Option 2: Create pyrightconfig.json

Create `pyrightconfig.json` in project root:

```json
{
  "typeCheckingMode": "basic",
  "useLibraryCodeForTypes": true,
  "extraPaths": [
    "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
  ],
  "executionEnvironments": [
    {
      "root": ".",
      "extraPaths": [
        "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
      ]
    }
  ]
}
```

**Benefits:**
- Read by both cursorpyright and Pylance
- Standard Pyright configuration format
- Works across different editors

### Option 3: Combined Approach (Best Practice)

Use both workspace settings AND pyrightconfig.json:

1. **Add to `.vscode/settings.json`**:
   ```json
   {
     "python.languageServer": "None",
     "python.jediEnabled": false,
     "cursorpyright.analysis.extrapaths": [
       "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
     ],
     "cursorpyright.analysis.typeCheckingMode": "basic",
     "cursorpyright.analysis.autoImportCompletions": true,
     "cursorpyright.analysis.indexing": true,
     "python.analysis.typeCheckingMode": "off",
     "python.analysis.extraPaths": [
       "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
     ],
     "python.analysis.stubPath": "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117",
     "editor.semanticHighlighting.enabled": true,
     "editor.semanticTokenColorCustomizations": {
       "enabled": true,
       "rules": {
         "namespace": "#4EC9B0",
         "class": "#4EC9B0",
         "function": "#DCDCAA",
         "variable": "#9CDCFE",
         "parameter": "#9CDCFE",
         "property": "#9CDCFE",
         "module": "#4EC9B0"
       }
     }
   }
   ```

2. **Create `pyrightconfig.json`**:
   ```json
   {
     "typeCheckingMode": "basic",
     "useLibraryCodeForTypes": true,
     "extraPaths": [
       "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
     ],
     "executionEnvironments": [
       {
         "root": ".",
         "extraPaths": [
           "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
         ]
       }
     ]
   }
   ```

**Benefits:**
- Maximum compatibility
- Works with both Cursor and VS Code
- Redundant configuration ensures it works even if one method fails
- Semantic highlighting for better code visualization

## Key Differences Summary

| Setting | VS Code/Pylance | Cursor/cursorpyright | Current Project |
|---------|----------------|---------------------|-----------------|
| Language Server | Pylance | cursorpyright (via `python.languageServer: "None"`) | Not configured |
| Path Setting | `python.analysis.extraPaths` | `cursorpyright.analysis.extrapaths` | Only has `python.analysis.extraPaths` |
| Config File | `pyrightconfig.json` (optional) | `pyrightconfig.json` (recommended) | Missing |
| User Settings | Global override | Global override (points to wrong project) | Points to telepass-blender |
| Semantic Highlighting | Configured | Configured | Not configured |

## Semantic Highlighting Configuration

### Why `bpy` May Not Be Highlighted

Even when autocompletion works, semantic highlighting may not work if:

1. **Semantic highlighting is disabled** - Need `editor.semanticHighlighting.enabled: true`
2. **Semantic token rules not configured** - Need `editor.semanticTokenColorCustomizations` with module/namespace rules
3. **TextMate rules missing** - Need `editor.tokenColorCustomizations.textMateRules` for Python module names
4. **Theme doesn't support semantic tokens** - Some themes may override semantic token colors
5. **Language server not providing semantic tokens** - cursorpyright needs to recognize `bpy` as a module

### Required Settings for Highlighting

```json
{
  "editor.semanticHighlighting.enabled": true,
  "editor.semanticTokenColorCustomizations": {
    "enabled": true,
    "rules": {
      "namespace": "#4EC9B0",
      "module": "#4EC9B0"
    }
  },
  "editor.tokenColorCustomizations": {
    "textMateRules": [
      {
        "scope": [
          "entity.name.type.module.python",
          "entity.name.namespace.python"
        ],
        "settings": {
          "foreground": "#4EC9B0"
        }
      }
    ]
  }
}
```

### Troubleshooting Highlighting Issues

1. **Check if semantic tokens are enabled**:
   - Open Command Palette (`Ctrl+Shift+P`)
   - Run "Developer: Inspect Editor Tokens and Scopes"
   - Click on `bpy` - should show semantic token information

2. **Verify language server is providing tokens**:
   - Check Output panel → "basedpyright" or "Cursor - Pyright"
   - Should show semantic token requests/responses

3. **Test with different themes**:
   - Some themes override semantic token colors
   - Try switching to a theme that supports semantic highlighting (e.g., Dark+, Light+)

4. **Reload window after configuration changes**:
   - `Ctrl+Shift+P` → "Developer: Reload Window"
   - Or restart Cursor completely

## Verification Steps

After applying the solution:

1. **Restart Cursor** completely
2. **Open a Python file** with `import bpy`
3. **Type `bpy.`** and wait 2-3 seconds - should see autocomplete
4. **Hover over `bpy`** - should show type information
5. **Check highlighting** - `bpy` should be colored (typically cyan/teal: #4EC9B0)
6. **Check Output panel** (`View → Output`):
   - Select "basedpyright" or "Cursor - Pyright"
   - Should show: "Loading configuration file at .../pyrightconfig.json"
   - Should show: "Found X source files"
   - Should NOT show errors about missing modules
7. **Inspect tokens** (if highlighting not working):
   - `Ctrl+Shift+P` → "Developer: Inspect Editor Tokens and Scopes"
   - Click on `bpy` to see what token type it's recognized as

## References

- Documentation: `D:\ProgramData\telepass-blender\debug\python_language_server\Use Python Language Server and IntelliSense in Cursor.md`
- Working configuration: `D:\ProgramData\telepass-blender\.vscode\settings.json`
- Pyright config: `D:\ProgramData\telepass-blender\pyrightconfig.json`
- Separation script: `D:\ProgramData\telepass-blender\debug\python_language_server\separate_cursor_vscode_settings.py`

## User-Level Configuration (Global Settings)

### ✅ Recommended: Configure at User Level

For maximum convenience, configure bpy highlighting and autocompletion at the **user level** so all projects automatically inherit the settings.

**Cursor User Settings** (`%USERPROFILE%\.cursor\User\settings.json`):
```json
{
    "python.languageServer": "None",
    "python.jediEnabled": false,
    "cursorpyright.analysis.extrapaths": [
        "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117"
    ],
    "cursorpyright.analysis.typeCheckingMode": "basic",
    "cursorpyright.analysis.autoImportCompletions": true,
    "cursorpyright.analysis.indexing": true
}
```

**Benefits:**
- ✅ Works automatically for ALL projects
- ✅ No need to configure each project individually
- ✅ Consistent bpy support across all Blender-related projects
- ✅ Projects can still override with workspace settings if needed

**Note:** The user settings now only include the shared bpy modules path (`D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117`). Project-specific paths (like venv paths) should be added in workspace settings if needed.

### Project-Specific Overrides

If a project needs additional paths (e.g., project-specific venv), add them in `.vscode/settings.json`:
```json
{
  "cursorpyright.analysis.extrapaths": [
    "D:/ProgramData/blender-addon/fake_bpy_modules_2.93-20230117",
    "./venv/Lib/site-packages"
  ]
}
```

Workspace settings will merge with user settings, so both paths will be available.

## Conclusion

The current project lacks cursorpyright-specific configuration. While it has VS Code-compatible settings (`python.analysis.extraPaths`), Cursor's language server requires `cursorpyright.analysis.extrapaths` to be configured.

**Solution Applied:** Updated Cursor user settings to include the shared bpy modules path globally, so all projects now automatically have bpy highlighting and autocompletion support. Individual projects can still add project-specific paths in workspace settings if needed.
