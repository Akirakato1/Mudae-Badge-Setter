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
5. Optionally enter `Budget kakera`. The `+` buttons disable when the next badge level would push the plan over budget, while `-` still works so you can tick counts down.
6. Set each badge count from `0` to `4`.
7. Check the live total cost and the next-level cost shown under each badge.
8. Click `Edit Badge Cost` to change the badge prices used by the cost display.
9. Click `New` to clear the name and badge counts for a fresh configuration.
10. Optionally enter a configuration name and click `Save / Update` to save the current badge counts.
11. Click `Delete` to remove the selected or named configuration.
12. Click `Set`.

Click the `?` button in the lower-left corner of the app to show these usage notes inside the app. In that help popup, click `userID` to see how to find and copy your Discord ID.
Click a badge name to show its costs, prerequisites, and perks.

The app sends:

```text
$kakerarefund <@user_id>
confirm
```

Then it sends one `$<badge> <target level>` command plus `y` for each selected badge count above `0`, such as `$bronze 3` then `y`.
If ruby is set to `4`, the app chooses the cheapest valid Ruby prerequisite path first, sends those badge commands, then sends `$ruby 4`, then sends the remaining badge commands.
The total cost display uses that same order, so prerequisite levels bought before Ruby IV are full price and later eligible levels get Ruby IV's 25% discount.

## Focus Behavior

When you click `Set`, the app focuses Discord, clicks near the lower center of the Discord window to focus the current channel message box, pastes each command, presses Enter, then leaves Discord focused. If Discord is already open, the app does not call Windows restore on it, so a maximized Discord window should keep its size.

If Discord misses messages, increase the message delay.

## Saved Configurations

Saved configurations are written to `%APPDATA%\Mudae Badge Setter\configs.json`. This file stores badge counts only. On first launch after an update, the app migrates older config files into AppData if AppData does not already have the new file.

If `configs.json` is empty or missing, the app seeds three built-in configurations: `Ruby 4 Minimum Cost`, `Sapphire 4 Minimum Cost`, and `Emerald 4 Minimum Cost`.

Clicking a saved configuration loads only its badge counts into the UI. `New` clears the current name, list selection, and badge counts so you can build a fresh configuration. Saving again with the same name updates it. `Delete` removes the selected configuration, or the configuration named in the text field if none is selected.

The app keeps permanent user ID, delay, and budget settings in `%APPDATA%\Mudae Badge Setter\settings.json`. This file stores only `user_id`, `delay`, and `budget`. Those fields are restored automatically the next time you open the app; the previous badge configuration is not auto-loaded.

Badge costs are written to `%APPDATA%\Mudae Badge Setter\badge_data.json`. On first launch, the app creates this file with the built-in default badge costs, prerequisites, perks, and default configuration definitions. Click `Edit Badge Cost` to edit the cost grid in the app; the app immediately uses the saved costs for total cost, next-level cost, and badge info displays.

Badge inputs are locked at `0` until their prerequisites are met. If a badge was already selected and you lower another badge so the prerequisite becomes unmet, the locked badge resets to `0` and becomes uneditable again. Bronze, Silver, Gold, and Diamond are always available. Sapphire unlocks with Bronze I, Silver I, and Gold I, or any two other Level IV badges. Ruby unlocks with Bronze II, Silver II, and Gold II, or any two other Level IV badges. Emerald unlocks with Bronze III, Silver III, and Gold III, or any two other Level IV badges.

After a successful run, the popup says `Set to <configuration name>` when the current badge counts match a saved configuration. If they do not match a saved configuration, it uses the badge-count sequence instead, such as `Set to 3420000` for bronze 3, silver 4, gold 2, and the remaining badges 0.
