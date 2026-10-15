# Start a plugin release from Designer CI

A Designer release should make a plugin release with the same number.
This page shows the change for `disguise-one/d3`. It is not applied yet.

## What happens

1. The Designer release workflow (`finalise_release.yml` in `disguise-one/d3`) finishes.
2. A new job starts the `release` workflow in this repository.
3. The `release` workflow copies the skill from the Designer release tag and opens a pull request.
4. A person merges the pull request.
5. The `tag` workflow makes the tag `disguise-designer--v<version>`.

## Version number

Designer release numbers look like `r34.0.1`. The plugin version drops the `r`: `34.0.1`.
The `d3` ref is the release tag: `release/r34.0.1`.

## Second GitHub App

The job needs a token that can start a workflow in this repository. Use a second GitHub App.
Do not widen the read-only App that reads `d3`. An App has one permission set for all repositories it is installed on.

- Name: `disguise-designer-plugin-release`
- Owner: `disguise-one`
- Installed on: `disguise-one/designer-claude-plugin` only
- Repository permissions: **Actions: Read and write**. No other permission.
- Webhook: not active
- Secrets in `disguise-one/d3`: `PLUGIN_APP_ID` and `PLUGIN_APP_PRIVATE_KEY`

## Job to add to `finalise_release.yml`

```yaml
  start-plugin-release:
    needs: merge-release-tag
    runs-on: ubuntu-latest
    steps:
      - name: Get a token for the plugin repository
        id: plugin-token
        uses: actions/create-github-app-token@v2
        with:
          app-id: ${{ secrets.PLUGIN_APP_ID }}
          private-key: ${{ secrets.PLUGIN_APP_PRIVATE_KEY }}
          owner: disguise-one
          repositories: designer-claude-plugin

      - name: Start the plugin release
        env:
          GH_TOKEN: ${{ steps.plugin-token.outputs.token }}
          RELEASE_VERSION: ${{ github.event.inputs.release_version }}
        run: |
          version="${RELEASE_VERSION#r}"
          gh workflow run release.yml \
            --repo disguise-one/designer-claude-plugin \
            -f version="$version" \
            -f d3_ref="release/${RELEASE_VERSION}"
```

The change goes through the normal `d3` branch and ticket rules. It needs a DSOF ticket.
