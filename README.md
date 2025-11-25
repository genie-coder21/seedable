# Seedable

**Torznab Proxy for Cross-Seedable Torrents**

Seedable is a middleware service that filters NZBHydra2 search results to only show torrents available on 2 or more trackers, ensuring every download has cross-seeding potential.

## What It Does

When you search for content in Sonarr/Radarr:
1. **Sonarr/Radarr** sends a search request to Seedable
2. **Seedable** queries NZBHydra2 for results from all your indexers
3. **Groups** results by normalized title and size
4. **Filters** to only keep torrents that exist on **2+ trackers**
5. **Returns** only cross-seedable results to Sonarr/Radarr

**Result:** Your search results are automatically curated to show only torrents you can cross-seed!

## Why You Need This

- **Save time:** No more manually checking if a torrent can be cross-seeded
- **Cleaner interface:** Only see relevant results in Sonarr/Radarr
- **Maximize seeding:** Every download guarantees cross-seed potential
- **Efficiency:** Works seamlessly with your existing setup

## Requirements

- Docker and Docker Compose
- NZBHydra2 (configured with multiple Torznab indexers)
- Sonarr and/or Radarr
- cross-seed (optional, but recommended)

## Quick Start

### 1. Clone or Download

```bash
cd /opt
mkdir seedable
cd seedable
# Copy all files to this directory
```

### 2. Generate API Key

Generate a secure API key to protect your Seedable instance:

```bash
# Option 1: Using Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Option 2: Using OpenSSL
openssl rand -hex 32

# Option 3: Using /dev/urandom
cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 43 | head -n 1
```

Copy the generated key - you'll need it for both docker-compose.yml and Sonarr/Radarr configuration.

### 3. Get API Keys

**Radarr API Key** (in Radarr UI):
1. Go to **Settings** → **General**
2. Scroll to **Security** section
3. Copy the **API Key**

**Sonarr API Key** (in Sonarr UI):
1. Go to **Settings** → **General**
2. Scroll to **Security** section
3. Copy the **API Key**

**NZBHydra2 API Key** (optional, only if authentication is enabled):
1. Go to **Config** → **Main**
2. Scroll to **Security** section
3. Copy the **API Key**

### 4. Configure

Edit `docker-compose.yml` and set your configuration:

```yaml
environment:
  - NZBHYDRA_URL=http://YOUR_SERVER_IP:5076   # Your NZBHydra2 URL
  # - NZBHYDRA_API_KEY=                       # Optional: NZBHydra2 API key (if auth enabled)

  - API_KEY=your-seedable-api-key-here        # Your generated Seedable API key

  # HIGHLY RECOMMENDED: Add Radarr/Sonarr API keys for efficient searching
  # Without these, searches will return 800+ results and filter slowly
  # With these, searches return ~20 relevant results instantly
  - RADARR_URL=http://YOUR_SERVER_IP:7878
  - RADARR_API_KEY=your-radarr-api-key-here
  - SONARR_URL=http://YOUR_SERVER_IP:8989
  - SONARR_API_KEY=your-sonarr-api-key-here

  - MIN_DUPLICATES=2                         # Minimum trackers required
  - SIZE_TOLERANCE_PERCENT=2.0               # Size matching tolerance
```

### 5. Deploy

```bash
docker-compose up -d
```

### 6. Verify

Visit `http://YOUR_SERVER_IP:5000` to see the status page.

### 7. Add to Sonarr/Radarr

**In Sonarr:**
1. Go to **Settings** → **Indexers** → **Add** → **Custom** → **Torznab**
2. **Name:** `Seedable`
3. **URL:** `http://YOUR_SERVER_IP:5000` ⚠️ **DO NOT include `/api` - Sonarr adds it automatically**
4. **API Key:** (the API_KEY you set in docker-compose.yml)
5. **Categories:** ⚠️ **IMPORTANT: You MUST select category 5000 (TV)** - this is the main category that most results use
   - ✅ **5000 (TV)** ← **REQUIRED! Most TV torrents use this category**
   - ✅ 5030 (TV SD) - Optional
   - ✅ 5040 (TV HD) - Optional
   - ✅ 5045 (TV UHD) - Optional
   - ✅ 5020 (TV Foreign) - Optional
   - ✅ 5070 (TV Anime) - Optional
   - ✅ 5080 (TV Documentary) - Optional
6. **Enable RSS Sync:** Disabled (recommended for Seedable)
7. **Enable Automatic Search:** Yes
8. **Enable Interactive Search:** Yes
9. Click **Test** → Should show green checkmark ✓
10. Click **Save**

**In Radarr:**
1. Go to **Settings** → **Indexers** → **Add** → **Custom** → **Torznab**
2. **Name:** `Seedable`
3. **URL:** `http://YOUR_SERVER_IP:5000` ⚠️ **DO NOT include `/api` - Radarr adds it automatically**
4. **API Key:** (the API_KEY you set in docker-compose.yml)
5. **Categories:** ⚠️ **IMPORTANT: You MUST select category 2000 (Movies)** - this is the main category that most results use
   - ✅ **2000 (Movies)** ← **REQUIRED! Most movie torrents use this category**
   - ✅ 2010 (Movies Foreign) - Optional
   - ✅ 2040 (Movies HD) - Optional
   - ✅ 2045 (Movies UHD) - Optional
   - ✅ 2030 (Movies SD) - Optional
   - ✅ 2020 (Movies Other) - Optional
6. **Enable RSS Sync:** Disabled (recommended for Seedable)
7. **Enable Automatic Search:** Yes
8. **Enable Interactive Search:** Yes
9. Click **Test** → Should show green checkmark ✓
10. Click **Save**

**Common Issues:**
- ❌ **"Query successful, but no results in the configured categories":** You forgot to select the **main category** (5000 for TV or 2000 for Movies)!
  - NZBHydra2 assigns most torrents to the main category, not subcategories
  - **Solution:** Edit your indexer settings and check category 5000 (TV) or 2000 (Movies)
- ❌ **404 Error:** You included `/api` in the URL - remove it!
  - **Wrong:** `http://YOUR_SERVER_IP:5000/api`
  - **Correct:** `http://YOUR_SERVER_IP:5000`
- ❌ **403 Invalid API Key:** Check that the API key matches exactly between docker-compose.yml and Sonarr/Radarr

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NZBHYDRA_URL` | `http://localhost:5076` | URL to your NZBHydra2 instance |
| `NZBHYDRA_API_KEY` | _(empty)_ | NZBHydra2 API key (optional, only if auth enabled) |
| `API_KEY` | `seedable-default-key` | API key for Sonarr/Radarr authentication |
| `RADARR_URL` | `http://localhost:7878` | URL to your Radarr instance (optional but recommended) |
| `RADARR_API_KEY` | _(empty)_ | Radarr API key (optional but recommended) |
| `SONARR_URL` | `http://localhost:8989` | URL to your Sonarr instance (optional but recommended) |
| `SONARR_API_KEY` | _(empty)_ | Sonarr API key (optional but recommended) |
| `MIN_DUPLICATES` | `2` | Minimum trackers a torrent must be on |
| `SIZE_TOLERANCE_PERCENT` | `2.0` | Allowed size variance for grouping (±%) |
| `PRIVATE_TRACKERS` | _(empty)_ | Comma-separated list of private tracker names (optional) |
| `PORT` | `5000` | Port to run the service on |
| `HOST` | `0.0.0.0` | Host to bind to |

### Why Radarr/Sonarr API Keys?

When Radarr/Sonarr searches for a specific movie/show, they send only an IMDb/TVDb ID. Without the API keys:
- ❌ NZBHydra2 returns **800+ random torrents** (can't filter by ID alone)
- ❌ Seedable filters them down manually = **slow searches**
- ❌ Higher resource usage

With the API keys:
- ✅ Seedable looks up "28 Days Later" from IMDb ID `tt0289043`
- ✅ NZBHydra2 returns **~20 relevant torrents** matching the title
- ✅ **Instant results** with minimal filtering
- ✅ Much more efficient

**The API keys are optional but highly recommended for performance.**

### Private Tracker Prioritization

Seedable can be configured to prioritize private trackers and filter out public-only results. This feature is useful if you:
- Have a mix of public and private trackers in NZBHydra2
- Only want to download from public trackers if you can cross-seed to private trackers
- Want to maximize upload on private trackers

**How it works:**
1. Configure `PRIVATE_TRACKERS` with your private tracker names (as they appear in NZBHydra2)
2. Seedable groups torrents and counts how many are from private vs public trackers
3. **Groups with ONLY public trackers are filtered out**
4. Groups with at least 1 private tracker are kept (including their public tracker duplicates)
5. Each result is labeled with `[PUB:X PRI:Y]` showing tracker counts

**Example Configuration:**

First, check how your trackers appear in NZBHydra2 (Settings → Indexers → Name column). Then add them to docker-compose.yml:

```yaml
- PRIVATE_TRACKERS=TorrentLeech,IPTorrents,PassThePopcorn,BroadcasTheNet,Nebulance
```

**Result Labels:**

When configured, torrents will show labels **at the front** for easy sorting and visibility:
- `[PRI:2 PUB:1] The.Matrix.1999.1080p.AMZN.WEB-DL` - 2 private trackers, 1 public tracker
- `[PRI:3 PUB:0] Interstellar.2014.2160p.BluRay` - Private-only (3 private trackers)
- `[PRI:1 PUB:2] Avatar.2009.1080p.BluRay` - 1 private tracker, 2 public trackers

The labels appear at the beginning so you can quickly identify and sort by tracker distribution!

**Filtering Behavior:**

Without `PRIVATE_TRACKERS` set:
- ✅ Shows all torrents on 2+ trackers (public or private)

With `PRIVATE_TRACKERS` set:
- ✅ Shows torrents on 2+ trackers where at least 1 is private
- ❌ Filters out torrents that exist only on public trackers

This ensures you can download from public trackers knowing you'll be able to cross-seed to private trackers!

### Adjusting Filtering

**More restrictive (only torrents on 3+ trackers):**
```yaml
- MIN_DUPLICATES=3
```

**More lenient size matching (useful for different releases):**
```yaml
- SIZE_TOLERANCE_PERCENT=5.0
```

**Stricter size matching:**
```yaml
- SIZE_TOLERANCE_PERCENT=1.0
```

## How It Works

### Grouping Logic

Torrents are grouped by:
1. **Normalized title:** Lowercase, dots/underscores removed, standardized spacing
2. **Size bucket:** Files grouped into size buckets (accounts for slight variations)

### Filtering Logic

**Step 1: Cross-Seed Filtering**
Only groups with `MIN_DUPLICATES` or more torrents are returned.

**Step 2: Private Tracker Prioritization (Optional)**
If `PRIVATE_TRACKERS` is configured, groups with ONLY public trackers are filtered out.

**Example (with private tracker prioritization enabled):**

NZBHydra2 returns:
- `The.Matrix.1999.1080p.BluRay.x264` (PrivateTracker1 only - 1 private) → **FILTERED (below min duplicates)**
- `The.Matrix.1999.1080p.AMZN.WEB-DL` (PrivateTracker1, PrivateTracker2 - 2 private) → **KEPT** → Shows as `[PRI:2 PUB:0]`
- `The.Matrix.1999.1080p.WEB-DL.H264` (TheRARBG, LimeTorrents - 2 public) → **FILTERED (public-only)**
- `The.Matrix.1999.2160p.UHD.BluRay` (PrivateTracker1, PrivateTracker2, PublicTracker1 - 2 private, 1 public) → **KEPT** → Shows as `[PRI:2 PUB:1]`
- `The.Matrix.1999.720p.BluRay` (PublicTracker1 only - 1 public) → **FILTERED (below min duplicates)**

Sonarr/Radarr receives only groups that meet BOTH requirements:
1. Available on 2+ trackers
2. At least 1 private tracker (if configured)

## Workflow Example

1. **User searches** for "The Matrix 1999" in Radarr
2. **Radarr** queries Seedable: `GET /api?t=movie&q=The+Matrix+1999`
3. **Seedable** queries NZBHydra2: `POST /internalapi/search`
4. **NZBHydra2** searches all configured indexers (public + private)
5. **Seedable** groups 300+ results → finds 50 unique releases
6. **Seedable** filters to 15 cross-seedable releases (on 2+ trackers)
7. **Seedable** applies private tracker prioritization (if configured) → 10 results remain
8. **Radarr** displays the 10 filtered results with tracker labels:
   - `[PRI:2 PUB:1] The.Matrix.1999.1080p.AMZN.WEB-DL.DDP5.1.H.264`
   - `[PRI:3 PUB:0] The.Matrix.1999.2160p.UHD.BluRay.x265`
   - `[PRI:1 PUB:2] The.Matrix.1999.1080p.BluRay.x264`
9. **User downloads** one result
10. **cross-seed** automatically finds and adds the other trackers from the same group

## Troubleshooting

### "Query successful, but no results in the configured categories"

**This is the #1 most common issue!** You forgot to select the main category.

**Solution:**
1. Go to Sonarr/Radarr → **Settings** → **Indexers**
2. Edit the Seedable indexer
3. Check the **main category**:
   - **Sonarr:** Check **5000 (TV)**
   - **Radarr:** Check **2000 (Movies)**
4. Save and test again

**Why?** NZBHydra2 assigns most torrents to the main category (5000 or 2000), not the subcategories (5030, 5040, etc.). If you only select subcategories, you'll get zero results even though Seedable is working correctly!

### No results in Sonarr/Radarr

**Check Seedable logs:**
```bash
docker logs seedable
```

Look for lines like:
```
Category filtered to 0 results matching ['5030', '5040', '5070']
```
If you see this, you forgot the main category (5000 for TV or 2000 for Movies)!

**Verify NZBHydra2 is accessible:**
```bash
curl http://YOUR_SERVER_IP:5076/internalapi/search \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"test","category":"All"}'
```

**Lower MIN_DUPLICATES temporarily:**
```yaml
- MIN_DUPLICATES=1  # Shows all results (no filtering)
```

### Too few results

- Lower `MIN_DUPLICATES` to 2 (if set higher)
- Increase `SIZE_TOLERANCE_PERCENT` to 3-5%
- Check that NZBHydra2 has multiple indexers configured

### API key errors

Make sure the API key in Sonarr/Radarr matches the `API_KEY` in docker-compose.yml.

### Connection refused

- Check that Seedable is running: `docker ps | grep seedable`
- Verify port 5000 is not in use: `ss -tlnp | grep 5000`
- Check firewall rules if accessing remotely

## Advanced Usage

### Using with Existing Networks

If you have a custom Docker network:

```yaml
networks:
  media:
    external: true
```

### Custom Port

```yaml
ports:
  - "7000:5000"  # Map host port 7000 to container port 5000
```

Then use `http://YOUR_SERVER_IP:7000/api` in Sonarr/Radarr.

### Health Monitoring

Seedable includes a health check endpoint:

```bash
curl http://YOUR_SERVER_IP:5000/health
```

Response:
```json
{
  "status": "healthy",
  "min_duplicates": 2
}
```

## Integration with cross-seed

Seedable and cross-seed complement each other:

**Seedable:** Filters searches to only show cross-seedable torrents
**cross-seed:** Automatically adds matching torrents from other trackers

**Workflow:**
1. Seedable ensures you download a cross-seedable release
2. cross-seed detects the download and searches for matches
3. cross-seed injects matching .torrent files to your client
4. You're now seeding to multiple trackers automatically

## Performance

- **Latency:** Adds ~1-3 seconds to search requests (NZBHydra2 query + filtering)
- **Resource usage:** Minimal (~50MB RAM, negligible CPU)
- **Scalability:** Handles typical home media server loads easily

## Limitations

- Requires NZBHydra2 (does not work directly with Prowlarr)
- Only filters torrents (not NZB/Usenet)
- Grouping is based on title/size heuristics (not perfect matching)

## Contributing

Contributions welcome! Please:
1. Test your changes thoroughly
2. Update documentation as needed
3. Follow existing code style

## License

MIT License - feel free to use, modify, and distribute.

## Credits

Built with love for the arr/cross-seed community.

## Support

Found a bug? Have a feature request?
Open an issue on GitHub!

---

**Seedable** - Because every download should be cross-seedable.
