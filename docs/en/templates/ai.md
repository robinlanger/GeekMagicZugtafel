# ai

![Preview of the ai page with provider claude](../../img/templates/ai-claude.png)

## What it shows

How much of an AI plan or budget you have used. Each page shows one provider, which you pick with `provider:`. If you use several, add several pages.

| `provider` | Shows | How the data gets there |
| --- | --- | --- |
| `claude` | Your Claude plan limits: the 5-hour window and the week, each in percent with the time of the next reset | Claude Code on your computer sends them to the server (push) |

For each limit there is a line with its name and the time of the reset on the right, and below it a wide bar with the value inside. The bar is green, orange from 75 % and red from 90 %.

For `claude`:

- **Reset:** less than a day away as `in 2:13` (hours:minutes), otherwise as weekday and time, for example `Thu 09:00`. If the reset time has already passed, the bar shows `0 %` and `reset`.
- **Age:** at the bottom the page always shows when the values arrived, for example `As of 13:58`.
- **No data yet:** until the first values arrive the page shows the notice `No data yet` with `Set up the status-line script`.
- **No limit data:** values arrived but without usable limits, for example after the `curl` test under [When something is wrong](#when-something-is-wrong). The next answer of Claude Code brings the real values. Claude Code only has limits with a Claude plan (Pro or Max); with an API key the script sends nothing and the page stays on `No data yet`.
- If your plan has no weekly limit, only the 5-hour bar appears.

## What you need

For `claude`:

- A Claude plan (Pro or Max) and [Claude Code](https://code.claude.com/docs) on a computer in the same home network as the Glance Box server.
- `curl` on that computer (macOS and Linux have it). On Windows, PowerShell is enough.
- The script `tools/statusline/glancebox-statusline.sh` (macOS, Linux) or `tools/statusline/glancebox-statusline.ps1` (Windows) from this repository on that computer.

Claude Code hands a small JSON text to its [status line](https://code.claude.com/docs/en/statusline) after every answer. It includes your limits (`rate_limits`). The script passes this text on to the server in the background and then shows your normal status line.

## Example

```yaml
- type: ai
  provider: claude
  lang: en
  refresh: 30
```

## Options

| Key | Default | Meaning |
| --- | --- | --- |
| `provider` | | Where the values come from: `claude`. Required. |
| `title` | name of the provider (`Claude`) | Header text. |
| `lang` | top-level `lang` | `de` or `en`. Sets all texts on the page. |
| `refresh` | `refresh` default | For `claude` we recommend `30`. The page only reads what arrived, so this costs nothing. |
| `duration` | `interval` | How many seconds the page stays on the display. |

## Setup

### Claude

1. **Key for the server.** Create a key with `openssl rand -hex 24` and put it in `.env` next to `docker-compose.yml`:

   ```
   GLANCEBOX_PUSH_KEY=<the key>
   ```

   In `config.yaml` add at the top level:

   ```yaml
   push_key: ${GLANCEBOX_PUSH_KEY}
   ```

2. **The page.** Add the example to the `pages:` list in `config.yaml` and run `docker compose up -d` (a plain `restart` does not read `.env` again).

3. **Settings on your computer.** Create the file `~/.config/glancebox/push.env` with the address of the server and the same key, and make it readable only for you:

   ```sh
   mkdir -p ~/.config/glancebox
   cat > ~/.config/glancebox/push.env <<'EOF'
   GLANCEBOX_URL=http://192.168.1.10:8080
   GLANCEBOX_PUSH_KEY=<the key>
   EOF
   chmod 600 ~/.config/glancebox/push.env
   ```

   Use your server's address in the home network. If `XDG_CONFIG_HOME` is set, the file goes to `$XDG_CONFIG_HOME/glancebox/push.env`.

4. **The script.** Copy `tools/statusline/glancebox-statusline.sh` to a place of your choice, for example `~/.claude/glancebox-statusline.sh`, and make it executable with `chmod +x`.

5. **Claude Code.** Add to `~/.claude/settings.json`:

   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "~/.claude/glancebox-statusline.sh"
     }
   }
   ```

   The script itself prints nothing, so the status line stays empty.

6. **Check.** Ask Claude Code something. After the answer, open `http://<server>:8080/` and wait for the next refresh of the page (up to 30 seconds).

### Keeping your own status line

If you already have a status line, pass its command to the script as arguments. The script hands it the same JSON, and its output stays your status line:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/glancebox-statusline.sh ~/.claude/my-statusline.sh"
  }
}
```

### Windows

1. Create `%APPDATA%\glancebox\push.env` with the same two lines as in step 3.
2. Copy `tools\statusline\glancebox-statusline.ps1`, for example to `%USERPROFILE%\.claude\`.
3. In `%USERPROFILE%\.claude\settings.json`:

   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:/Users/<you>/.claude/glancebox-statusline.ps1"
     }
   }
   ```

   Write the path with forward slashes `/`: Claude Code may run the command through Git Bash, which swallows backslashes. An existing status line goes at the end of the command, as above. With Git Bash installed you can also use the `.sh` script as on macOS.

### Limits

- The values only update while Claude Code runs and gives answers, and only while your computer is in your home network. Away from home the sending fails silently and the page keeps showing the last values with their time (`As of 13:58`).
- The server keeps the values in RAM only. After a restart of the server the page shows `No data yet` until Claude Code gives its next answer.
- A new Claude Code session sends its limits only after its first answer.

## Privacy & security

- **Only `rate_limits` is stored.** The status-line JSON also contains things like the working folder and the session ID. The server drops everything except `rate_limits` straight away, writes nothing to disk and does not log the content.
- **No Anthropic token leaves your computer.** The script only sends the text Claude Code gives the status line, with the Glance Box key. The server never logs in to Anthropic.
- **The push key** only lets someone send values to your display. Keep it in `.env` on the server and in `push.env` (`chmod 600`) on your computer, never in `config.yaml`.
- The server and its push inbox are meant for your home network only. Do not make them reachable from the internet.

## When something is wrong

- **`No data yet` stays:** Claude Code only sends limits with a Claude plan (Pro or Max) and in recent versions. With an API key instead of a plan, or with an older Claude Code, the script sends nothing and the page stays on `No data yet`; nothing else is wrong then. Otherwise check that `push_key` is set and that you ran `docker compose up -d` after changing `.env`. Then test the way from your computer to the server: `curl -i -X POST -H "Authorization: Bearer <the key>" -H "Content-Type: application/json" -d '{"rate_limits":{}}' http://<server>:8080/api/v1/push/claude`. `204` is right (the page then shows `No limit data` until the next answer of Claude Code), `401` means the key differs, `404` means the server has no `push_key`. If `curl` works, check `push.env` (both lines, no spaces around `=`) and the path in `settings.json`.
- **`No limit data`:** a push arrived but without usable limit windows, for example the `curl` test above with `{"rate_limits":{}}`. The next answer of Claude Code replaces it with the real values.
- **The status line is empty:** that is normal without your own status line. To show one, pass its command as arguments.
- **The server refuses to start and names `provider`:** the value must be one of the providers in the table above.
