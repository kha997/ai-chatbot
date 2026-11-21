# Agent CLI readiness

Checked 2026-11-21 from the Windows Codex terminal, workspace `D:\Projects\AI ChatBot`. All three tools respond to informational commands. Authentication, provider access, available quota and prompt execution remain unverified.

| Agent | Observed executable | Version | Verification |
| --- | --- | --- | --- |
| Qoder | `%LOCALAPPDATA%\AIChatBotAgentCLI\qoder-native\qodercli.exe` | 1.1.94 | Native Windows x64, version and help exit 0. Help describes `--print` and output format. |
| OpenCode | `/usr/bin/opencode` in existing Ubuntu-24.04 WSL | 1.18.30 | Existing install reused. Codex called WSL and ran version and `run --help` with 15-second bounds, exit 0. |
| Kilo | `%LOCALAPPDATA%\AIChatBotAgentCLI\kilo\kilo.exe` | 7.8.32 | Native Windows x64 baseline build. Version, help and `run --help` exit 0. |

Windows PATH initially had no matching CLI. The separately installed Qoder GUI identified itself as desktop product version 0.4.11.0. Qoder's documented npm compatibility package 1.1.94 printed help but exited with a libuv assertion under the installed Node 25.6.1. The project-local npm package and its dependencies were removed after the native replacement passed. Existing Windows and WSL PATH values were preserved. Explicit executable paths and the WSL bridge avoid collisions and work in Codex without a terminal restart.

The native ZIPs were downloaded from the publishers and SHA-256 verified before extraction into user-local, project-specific directories. The Qoder manifest endpoint was identified by inspecting the installer linked by the vendor. The installation script itself was not executed. Sources accessed 2026-11-21. [Qoder installation](https://docs.qoder.com/cli/installation) · [Qoder manifest](https://qoder-ide.oss-accelerate.aliyuncs.com/qodercli/channels/manifest.json) · [Kilo release](https://github.com/Kilo-Org/kilocode/releases/tag/v7.8.32) · [OpenCode CLI](https://opencode.ai/docs/cli).

- Qoder archive SHA-256 `1c9f12cf0c57d44d87d8bc60a2a34dfc439fefb4b5884fe509c91f3e0ed0f121`
- Kilo archive SHA-256 `4f1f542baa28f21fbb4801dd01be661f4a164c27042c8156b3237ff15c7e4c59`

Run from PowerShell for a repeatable, zero-prompt check:

```powershell
& (Join-Path $env:LOCALAPPDATA 'AIChatBotAgentCLI\qoder-native\qodercli.exe') --version
wsl.exe -d Ubuntu-24.04 --exec timeout 15s /usr/bin/opencode --version
& (Join-Path $env:LOCALAPPDATA 'AIChatBotAgentCLI\kilo\kilo.exe') --version
```

Rollback the two new CLI installs by archiving the specific directories `qoder-native` and `kilo` under `%LOCALAPPDATA%\AIChatBotAgentCLI`. Move each by its literal path to an unused name in that same directory. Restore by reversing the rename. The pre-existing OpenCode and Qoder GUI are independent.

For a future model qualification, request separate authorization identifying provider/model, existing credential, permitted inputs, isolation, and a maximum spend/quota. Then run one bounded synthetic read-only prompt per approved tool and record actual usage. Help output alone does not establish that credentials, costs or runtime restrictions are suitable.
