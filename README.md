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
6. Check the live total cost and the next-level cost shown under each badge.
7. Optionally enter a configuration name and click `Save / Update` to save the current badge counts.
8. Click `Delete` to remove the selected or named configuration.
9. Click `Set`.

Click the `?` button in the lower-left corner of the app to show these usage notes inside the app. In that help popup, click `userID` to see how to find and copy your Discord ID.
Click a badge name to show its costs, prerequisites, and perks.

The app sends:

```text
$kakerarefund <@user_id>
confirm
```

Then it sends one `$<badge> <count>` command plus `y` for each selected badge count above `0`, such as `$bronze 3` then `y`.
If ruby is set to `4`, the app sends its prerequisites first, then `$ruby 4`, then the remaining badge commands.
The total cost display uses that same order, so prerequisite levels bought before Ruby IV are full price and later eligible levels get Ruby IV's 25% discount.

## Focus Behavior

When you click `Set`, the app briefly focuses Discord, clicks near the lower center of the Discord window to focus the current channel message box, pastes each command, presses Enter, then returns focus to the app.

If Discord misses messages, increase the message delay.

## Saved Configurations

Saved configurations are written to `%APPDATA%\Mudae Badge Setter\configs.json`. This file stores badge counts only. On first launch after an update, the app migrates older config files into AppData if AppData does not already have the new file.

If `configs.json` is empty or missing, the app seeds three built-in configurations: `Ruby 4 Minimum Cost`, `Sapphire 4 Minimum Cost`, and `Emerald 4 Minimum Cost`.

Clicking a saved configuration loads only its badge counts into the UI. Saving again with the same name updates it. `Delete` removes the selected configuration, or the configuration named in the text field if none is selected.

The app keeps permanent user ID and delay settings in `%APPDATA%\Mudae Badge Setter\settings.json`. This file stores only `user_id` and `delay`. Those fields are restored automatically the next time you open the app; the previous badge configuration is not auto-loaded.

Badge costs, prerequisites, perks, and built-in default definitions are kept in `badge_data.json`.

Badge inputs are locked until their prerequisites are met. Bronze, Silver, and Gold are always available. Ruby and Sapphire unlock with Bronze II, Silver II, and Gold II, or any two other Level IV badges. Emerald and Diamond unlock with any two other Level IV badges.

After a successful run, the popup says `Set to <configuration name>` when the current badge counts match a saved configuration. If they do not match a saved configuration, it uses the badge-count sequence instead, such as `Set to 3420000` for bronze 3, silver 4, gold 2, and the remaining badges 0.
