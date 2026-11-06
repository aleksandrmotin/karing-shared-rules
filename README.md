# Shared Karing rules

Edit **rules.json** in this repository. Saving a change to `main` starts GitHub Actions, validates the source, generates two sing-box Rule Sets and publishes only `dist/` to GitHub Pages.

- VPN: https://aleksandrmotin.github.io/karing-shared-rules/vpn.json
- Direct: https://aleksandrmotin.github.io/karing-shared-rules/direct.json
- Telegram: https://aleksandrmotin.github.io/karing-shared-rules/telegram.json
- Telegram source check: https://aleksandrmotin.github.io/karing-shared-rules/telegram-status.json
- Deployment status: https://github.com/aleksandrmotin/karing-shared-rules/actions

## Edit rules

`vpn` and `direct` accept `domain` (exact names), `domain_suffix`, and `ip_cidr` lists. For a new suffix covering both the root domain and its subdomains, omit the leading dot. Existing leading dots were retained to preserve the original matches. Do not put VPN subscription URLs, passwords or server credentials in this public repository.

After editing locally:

```sh
python3 build.py
python3 build.py --check
git add rules.json dist
git commit -m "Update routing rules"
git push
```

Editing rules.json in the GitHub web interface is sufficient; Actions rebuilds the published files even if the committed dist files have not been regenerated.

## Connect in Karing

For initial setup, import [`setup/karing-remote-import.json`](setup/karing-remote-import.json) from the custom-group list (**Diversion Rules → pencil → ⋮ → Import**), keep all 18 groups enabled and confirm. This native Karing import replaces the two manual lists with remote links and retains the other built-in groups. It contains no VPN subscriptions. Apply once on each device, then check group order and downloads. Do not import this setup file as a VPN profile or as a sing-box Rule Set.

In the existing custom routing groups, replace inline matchers with the corresponding URL in **Rule Set**. Keep these groups in this order:

1. VPN list: **Current Selected** (vpn.json).
2. Direct list: **Direct** (direct.json).
3. Existing built-in service groups, in their original order.

The VPN exception for a specific storage.googleapis.com hostname must remain above the broader direct .googleapis.com suffix. These remote files contain manual overrides only; existing built-in service groups are retained on each device. VPN providers and account settings remain device-specific.

Set **Settings → Diversion → Rule Set → Update interval** to 1 hour on each device. This is periodic polling, not instant push delivery; delivery while iOS is suspended or VPN is off must be verified separately. Check rule-set download and matches in Karing before removing the inline copies.

## Telegram updates

Actions downloads the [official Telegram networks](https://core.telegram.org/resources/cidr.txt) on every deployment and daily at approximately 03:17 UTC. GitHub may delay scheduled runs. The updater validates CIDRs, both address families, duplicates and unexpectedly broad networks. A download or validation failure stops deployment and leaves the previously published site in place. `telegram-status.json` reports the last successful source check and the checksum of the published rule set. Check Actions for failures; account notification preferences are not changed by this repository.

For an existing Telegram-specific group, keep OR and its assigned proxy server/group. Add the telegram.json URL to **Rule Set**, remove the static **IP Cidr** copy, and save. Built-in Telegram matchers can remain. Keep this group ahead of broader rules when Telegram must always use its own proxy group. No network-type condition is needed for a group that applies on both Wi-Fi and cellular.

The client must poll this URL (suggested Rule Set interval: 1 hour). Refresh while iOS is suspended or VPN is off is not guaranteed. This updates network membership only; it does not change proxy servers, credentials or device-specific group assignments.

GitHub [automatically disables schedules in public repositories after 60 days without repository activity](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows). To maintain activity, the daily workflow also archives a newly downloaded and validated Telegram snapshot in Git every 30 days. Only the archive job has `contents: write`; it uses the built-in repository token, commits only `dist/telegram.json` and `dist/telegram-status.json`, and never force-pushes. No personal access token or manual maintenance commit is required. The saved timestamp changes even when the IP ranges remain the same, recording a real successful source check. GitHub-token pushes do not recursively trigger another workflow.

For verification or recovery, **Run workflow → archive_snapshot** forces a snapshot on demand. Normal scheduled runs archive only when the last snapshot commit is at least 30 days old. Archiving runs after a successful Pages deployment, so the branch is not changed while that deployment is in progress. If source validation or GitHub operations fail, the workflow reports a failure rather than recording an unverified snapshot. Check the published status timestamp and Actions if updates appear stale.

The setup import is an initial configuration snapshot. Reimporting it after device-specific customizations may overwrite their settings; edit the existing group instead.

Validate Telegram locally with `python3 update_telegram.py --check`. To refresh it, run `python3 update_telegram.py`; internet access is required.

## Rule set validation

Both source files use version 1 of the sing-box source format. The initial lists were compiled with official sing-box 1.13.0 and checked with its native matcher, including precedence and negative-match cases. This does not replace on-device download and refresh testing.

- https://karing.app/en/app-manual/diversion-rule-edit
- https://sing-box.sagernet.org/configuration/rule-set/source-format/
