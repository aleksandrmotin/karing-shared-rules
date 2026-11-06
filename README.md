# Shared Karing rules

Edit **rules.json** in this repository. Saving a change to `main` starts GitHub Actions, validates the source, generates two sing-box Rule Sets and publishes only `dist/` to GitHub Pages.

- VPN: https://aleksandrmotin.github.io/karing-shared-rules/vpn.json
- Direct: https://aleksandrmotin.github.io/karing-shared-rules/direct.json
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

## Validate

Both source files use version 1 of the sing-box source format. The initial lists were compiled with official sing-box 1.13.0 and checked with its native matcher, including precedence and negative-match cases. This does not replace on-device download and refresh testing.

- https://karing.app/en/app-manual/diversion-rule-edit
- https://sing-box.sagernet.org/configuration/rule-set/source-format/
