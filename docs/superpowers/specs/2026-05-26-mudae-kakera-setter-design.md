# Mudae Kakera Setter Design

## Goal

Build a Windows Python desktop app that lets the user define Mudae kakera badge purchase counts, save/load named configurations, and run the configured command sequence in the currently open Discord text channel.

## Scope

The app is a local desktop automation helper. It does not use Discord APIs, bot tokens, or user tokens. It controls the already-open Discord desktop client by focusing the Discord window, focusing the visible channel message box, pasting commands, pressing Enter, and returning focus to the app window.

## User Interface

The app has these inputs:

- A Discord user ID text field at the top. The user enters only the numeric ID, for example `718568383347556424`.
- A message delay text field, defaulting to `0.8`, interpreted as seconds between sent messages.
- Seven badge count controls for `bronze`, `silver`, `gold`, `sapphire`, `ruby`, `emerald`, and `diamond`.
- Each badge count is a numeric spinner from `0` to `4`.
- A configuration name text field.
- A save/update configuration button.
- A list of existing saved configurations.
- A `Set` button that runs the configured Discord automation.

Clicking a saved configuration loads its user ID, delay, and badge counts into the current UI. Editing values and saving with the same name updates that saved configuration.

## Saved Configuration

Configurations are stored in a local JSON file named `mudae_kakera_configs.json` next to the script. The file stores a dictionary keyed by configuration name. Each configuration contains:

- `user_id`: string
- `delay`: float
- `badges`: object mapping badge name to integer count

Invalid or missing config data is handled by using defaults instead of crashing the app.

## Command Sequence

When the user clicks `Set`, the app validates the user ID and delay. A raw user ID such as `718568383347556424` becomes this exact first command:

```text
$kakerarefund <@718568383347556424>
```

The second command is:

```text
confirm
```

For each badge in this order:

```text
bronze, silver, gold, sapphire, ruby, emerald, diamond
```

the app sends the pair:

```text
$<badge>
y
```

The pair is repeated the configured number of times for that badge. A count of `0` sends no commands for that badge. A count of `4` sends the pair four times.

The app waits the configured delay between every message.

## Discord Automation

The app searches top-level Windows windows for one whose title includes `Discord`. It brings that window to the foreground, waits briefly, clicks near the lower center of the Discord window to focus the currently open channel's message box, and sends each message using clipboard paste plus Enter.

Using clipboard paste is preferred over simulated character typing because Discord commands are short, exact, and may include characters like `<`, `@`, and `$`. The app saves the previous clipboard text before running and restores it afterward when possible.

After all commands have been sent, the app returns focus to the app window.

## Error Handling

The app shows a dialog and does not send commands when:

- The user ID field is empty or contains non-digits.
- The delay is not a positive number.
- No Discord window can be found.

If an error occurs mid-run, the app attempts to restore the clipboard and return focus to the app window before showing the error.

## Testing

Automated tests cover pure behavior:

- Building the command sequence from user ID and badge counts.
- Validating user IDs.
- Validating delay input.
- Normalizing saved configuration data.

Manual verification covers the Windows UI and Discord interaction because it depends on the local desktop environment.
