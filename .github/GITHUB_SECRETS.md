# GitHub Secrets Configuration

This repository uses GitHub Secrets to manage sensitive data securely.

## Required Secrets

### 1. Container Registry Access
- **GITHUB_TOKEN** - Automatically provided by GitHub Actions
  - Used to authenticate with `ghcr.io`
  - Scopes: `packages:write`

### 2. Zotero API Configuration (Optional for build-time)

If you want to embed Zotero credentials in the Docker image at build-time:

- **ZOTERO_GROUP_ID** - Zotero group library ID
  - Example: `5767153`
  - Get from: https://www.zotero.org/groups/your-group/settings

- **ZOTERO_GROUP_API_KEY** - Zotero group API key
  - Get from: https://www.zotero.org/settings/keys
  - ⚠️ This will be embedded in the Docker image - keep image PRIVATE!

- **ZOTERO_PERSONAL_API_KEY** - Personal library API key (optional)
  - Get from: https://www.zotero.org/settings/keys

## Setup Instructions

### GitHub Repository Settings

1. Go to: **Settings → Secrets and variables → Actions**

2. Click **New repository secret**

3. Add each secret:
   - Name: `ZOTERO_GROUP_ID`
   - Value: Your group ID from Zotero

4. Repeat for:
   - `ZOTERO_GROUP_API_KEY`
   - `ZOTERO_PERSONAL_API_KEY` (optional)

### Rotating Secrets

When you regenerate API keys in Zotero:

1. Go to **Settings → Secrets and variables → Actions**
2. Click the secret name
3. Click **Update**
4. Paste new value
5. GitHub Actions will use new secret on next build

### Docker Image Privacy

⚠️ **Important:** Since secrets are embedded in the Docker image, **keep this repository PRIVATE**

- Images are pushed to `ghcr.io/BIH-CEI/zotero-comfort:latest`
- Only authenticated users can pull from private registry
- Consider rotating secrets if repository accidentally becomes public

## Workflow Behavior

```
On push to main:
  1. GitHub Actions triggered
  2. Build Docker image from Dockerfile
  3. Secrets available during build
  4. Image pushed to ghcr.io/BIH-CEI/zotero-comfort:latest
  5. Tests run against built image

On git tag (v1.0.0):
  1. Build triggered
  2. Image tagged: ghcr.io/BIH-CEI/zotero-comfort:v1.0.0
  3. Also tagged: ghcr.io/BIH-CEI/zotero-comfort:latest
```

## Using Built Images Locally

```bash
# Login to GitHub Container Registry
gh auth login --with-token < token.txt

# Pull latest image
docker pull ghcr.io/BIH-CEI/zotero-comfort:latest

# Or use in docker-compose.yml
image: ghcr.io/BIH-CEI/zotero-comfort:latest
```

## Security Notes

1. **Never commit secrets** - GitHub Actions prevents this
2. **Keep repo PRIVATE** - Images contain embedded credentials
3. **Rotate regularly** - Change API keys every 3-6 months
4. **Audit access** - Check who has access to this repository
5. **Use GitHub's secret scanning** - Enable in Settings → Security

## Troubleshooting

### Build fails with "API key not provided"
- Check that secrets are set in GitHub Settings
- Verify secret names match exactly: `ZOTERO_GROUP_ID`, `ZOTERO_GROUP_API_KEY`

### Image push fails
- Ensure `GITHUB_TOKEN` has `packages:write` scope
- Check repository is accessible (not archived/deleted)

### Tests fail after pull
- Verify Docker image was built successfully
- Check logs in GitHub Actions tab
- Try running locally: `docker run ghcr.io/BIH-CEI/zotero-comfort:latest`
