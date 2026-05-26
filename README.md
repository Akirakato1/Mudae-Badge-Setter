# Mudae Badge Setter

A small Windows Python UI for saving Mudae kakera badge configurations and sending the matching commands through the open Discord desktop client.

## Run

On this machine, use the Windows Python launcher because the default Anaconda `python` cannot start `tkinter`:

```powershell
py -3.7 mudae_badge_setter.py
```

If your normal Python has a working `tkinter`, this also works:

```powershell
python mudae_badge_setter.py
```

## Use

1. Open Discord desktop to the text channel where you want to interact with Mudae.
2. Run the app.
3. Enter your discord userID, for example `718568383347556424`.
4. Set the message delay. The default is `0.8` seconds.
5. Set each badge count from `0` to `4`.
6. Optionally enter a configuration name and click `Save / Update` to save the current badge counts.
7. Click `Delete` to remove the selected or named configuration.
8. Click `Set`.

Click the `?` button in the lower-left corner of the app to show these usage notes inside the app. In that help popup, click `userID` to see how to find and copy your Discord ID.

The app sends:

```text
$kakerarefund <@user_id>
confirm
```

Then it sends `$bronze`/`y`, `$silver`/`y`, `$gold`/`y`, `$sapphire`/`y`, `$ruby`/`y`, `$emerald`/`y`, and `$diamond`/`y` according to the counts you selected.

## Focus Behavior

When you click `Set`, the app briefly focuses Discord, clicks near the lower center of the Discord window to focus the current channel message box, pastes each command, presses Enter, then returns focus to the app.

If Discord misses messages, increase the message delay.

## Saved Configurations

Saved configurations are written to `%APPDATA%\Mudae Badge Setter\mudae_kakera_configs.json`. This file stores badge counts only. On first launch after an update, the app copies an older side-by-side config file into AppData if AppData does not already have one.

Clicking a saved configuration loads only its badge counts into the UI. Saving again with the same name updates it. `Delete` removes the selected configuration, or the configuration named in the text field if none is selected.

The app keeps permanent user ID and delay settings in `%APPDATA%\Mudae Badge Setter\mudae_kakera_last_state.json`. This file stores only `user_id` and `delay`. Those fields are restored automatically the next time you open the app; the previous badge configuration is not auto-loaded.

After a successful run, the popup says `Set to <configuration name>` when the current badge counts match a saved configuration. If they do not match a saved configuration, it uses the badge-count sequence instead, such as `Set to 3420000` for bronze 3, silver 4, gold 2, and the remaining badges 0.
