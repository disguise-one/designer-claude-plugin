# Start a plugin release from Designer CI

A Designer release makes a plugin release with the same number.
This page shows the change for `disguise-one/d3`. It is not applied yet.

## How a Designer release is made

A Designer release is a manual checklist with a release manager ("Manual Gold Release Process" in Confluence, space R&D).
Step 1 is the GitHub action **Create Gold Release Build**. It makes the tag `release/r<version>`, for example `release/r34.2.1`.
The release can be held back after that tag, for example for a regression. The release goes out on release day.

## When the plugin release is made

- **When the release tag goes up:** the plugin pull request is opened. It stays open.
- **On release day, when the release comes out:** a person merges the pull request. This is a new line in the release-day checklist.
- **After the merge:** the `tag` workflow makes the tag `disguise-designer--v<version>`. Users can then get the release.

If a release is held back and a new tag is made (for example `r34.2.2`), the new tag opens a new pull request. A person closes the old one.

## Steps

1. A person runs **Create Gold Release Build** in `disguise-one/d3`.
2. At the end of that workflow, a new job starts the `release` workflow in this repository.
3. The `release` workflow copies the skill from the release tag and opens a pull request.
4. The release goes out. A person merges the pull request.
5. The `tag` workflow makes the tag.

## Version number

The Designer version `34.2.1` is the plugin version `34.2.1`. The `d3` ref is the tag `release/r34.2.1`.
If the Designer version has no third number, use `0`. The workflow needs three numbers.

## Second GitHub App

The job needs a token that can start a workflow in this repository. Use a second GitHub App.
Do not widen the read-only App that reads `d3`. An App has one permission set for all repositories it is installed on.

- Name: `disguise-designer-plugin-release`
- Owner: `disguise-one`
- Installed on: `disguise-one/designer-claude-plugin` only
- Repository permissions: **Actions: Read and write**. No other permission.
- Webhook: not active
- Secrets in `disguise-one/d3`: `PLUGIN_APP_ID` and `PLUGIN_APP_PRIVATE_KEY`

## Job to add to `create_release_build.yml`

Add it after the job that pushes the tag. `d3_version` is the version of the release, for example `34.2.1`.
The existing job runs on a self-hosted Windows runner. The new job runs on a GitHub-hosted runner, so the version goes through a job output.

```yaml
  start-plugin-release:
    needs: create_release
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
          D3_VERSION: ${{ needs.create_release.outputs.d3_version }}
        run: |
          gh workflow run release.yml \
            --repo disguise-one/designer-claude-plugin \
            -f version="$D3_VERSION" \
            -f d3_ref="release/r${D3_VERSION}"
```

The `create_release` job must expose `d3_version` as an output. The change goes through the normal `d3` branch and ticket rules. It needs a DSOF ticket.

## LTSC and hotfix lines

A marketplace serves one plugin version at a time. Decide if the plugin follows only the newest line.
If it does, the job must skip LTSC releases.
