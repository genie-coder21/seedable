# Seedable

**Torznab Proxy for Cross-Seedable Torrents**

Seedable is a middleware service that filters NZBHydra2 search results to only show torrents available on 2 or more trackers, ensuring every download has cross-seeding potential.

**Works with both Private AND Public trackers!** Seedable helps you maximize your seeding efficiency whether you're on private trackers, public trackers, or a mix of both.

## Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────────┐
│              │         │              │         │                  │
│  Sonarr/     │ ------> │   Seedable   │ ------> │   NZBHydra2      │
│  Radarr      │ <------ │   (Proxy)    │ <------ │   (Indexers)     │
│              │         │              │         │                  │
└──────────────┘         └──────────────┘         └──────────────────┘
   Search Request         Filters Results           Queries All Trackers
   for "The Matrix"       to Cross-Seedable        (Private + Public)
```

Seedable sits between Sonarr/Radarr and NZBHydra2, automatically filtering search results to show only cross-seedable torrents.

## What It Does

When you search for content in Sonarr/Radarr:
1. **Sonarr/Radarr** sends a search request to Seedable
2. **Seedable** queries NZBHydra2 for results from all your indexers (private + public)
3. **Groups** results by normalized title and size
4. **Filters** to only keep torrents that exist on **2+ trackers**
5. **Labels** results with `[PRI:X PUB:Y]` showing tracker distribution
6. **Returns** only cross-seedable results to Sonarr/Radarr

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

## Recent Changes

**Configuration Simplified (.env file):**
- All configuration now uses a single `.env` file for easy management
- No more hardcoded credentials in docker-compose.yml
- Copy `.env.example` to `.env` and customize your settings
- docker-compose.yml automatically loads values from `.env`

## Quick Start

### 1. Clone or Download

**Option 1: Git Clone (Recommended)**
```bash
cd /opt
git clone https://github.com/genie-coder21/seedable.git
cd seedable
```

**Option 2: Manual Download**
```bash
cd /opt
mkdir seedable
cd seedable
# Download and extract files to this directory
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

Copy the example configuration file and edit it:

```bash
cp .env.example .env
nano .env
```

Edit `.env` and set your configuration:

```bash
# NZBHydra2 Configuration
NZBHYDRA_URL=http://YOUR_SERVER_IP:5076
NZBHYDRA_API_KEY=                            # Optional: Only if auth enabled

# Seedable API Key (use the key you generated in step 2)
API_KEY=your-seedable-api-key-here

# Radarr/Sonarr API Configuration (HIGHLY RECOMMENDED)
# Without these, searches return 800+ results and filter slowly
# With these, searches return ~20 relevant results instantly
RADARR_URL=http://YOUR_SERVER_IP:7878
RADARR_API_KEY=your-radarr-api-key-here
SONARR_URL=http://YOUR_SERVER_IP:8989
SONARR_API_KEY=your-sonarr-api-key-here

# Filtering Settings
MIN_DUPLICATES=2
SIZE_TOLERANCE_PERCENT=2.0

# ⚠️ CRITICAL: Private Tracker Prioritization
# ⚠️ YOU MUST SET THIS FOR SEEDABLE TO WORK PROPERLY!
# List your private tracker names exactly as they appear in NZBHydra2
# Without this, the filters will remove most/all results!
# Example: TorrentLeech,IPTorrents,PassThePopcorn
PRIVATE_TRACKERS=your,private,tracker,names,here

# Server Configuration
PORT=5000
HOST=0.0.0.0
```

**⚠️ IMPORTANT:** The `PRIVATE_TRACKERS` setting is **CRITICAL** for proper operation! See the "Private Tracker Configuration" section below for details.

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
4. **API Key:** (the API_KEY you set in .env file)
5. **Categories:** ⚠️ **CRITICAL: Select ALL TV categories (main category + subcategories)**

   **Select ALL of these:**
   - ✅ **5000 (TV)** ← **MAIN CATEGORY - REQUIRED!**
   - ✅ **5020 (TV Foreign)**
   - ✅ **5030 (TV SD)**
   - ✅ **5040 (TV HD)**
   - ✅ **5045 (TV UHD)**
   - ✅ **5050 (TV Other)**
   - ✅ **5060 (TV Sport)**
   - ✅ **5070 (TV Anime)**
   - ✅ **5080 (TV Documentary)**

   **Why select ALL categories?** Different indexers assign torrents to different categories. Some use the main category (5000), others use subcategories (5040, 5045, etc.). To ensure you see all available torrents, select every TV category.

6. **Enable RSS Sync:** Disabled (recommended for Seedable)
7. **Enable Automatic Search:** Yes
8. **Enable Interactive Search:** Yes
9. Click **Test** → Should show green checkmark ✓
10. Click **Save**

**In Radarr:**
1. Go to **Settings** → **Indexers** → **Add** → **Custom** → **Torznab**
2. **Name:** `Seedable`
3. **URL:** `http://YOUR_SERVER_IP:5000` ⚠️ **DO NOT include `/api` - Radarr adds it automatically**
4. **API Key:** (the API_KEY you set in .env file)
5. **Categories:** ⚠️ **CRITICAL: Select ALL Movie categories (main category + subcategories)**

   **Select ALL of these:**
   - ✅ **2000 (Movies)** ← **MAIN CATEGORY - REQUIRED!**
   - ✅ **2010 (Movies Foreign)**
   - ✅ **2020 (Movies Other)**
   - ✅ **2030 (Movies SD)**
   - ✅ **2040 (Movies HD)**
   - ✅ **2045 (Movies UHD)**
   - ✅ **2050 (Movies 3D)**
   - ✅ **2060 (Movies BluRay)**

   **Why select ALL categories?** Different indexers assign torrents to different categories. Some use the main category (2000), others use subcategories (2040, 2045, etc.). To ensure you see all available torrents, select every Movie category.

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

### Private Tracker Configuration

⚠️ **CRITICAL REQUIREMENT: You MUST configure your private trackers for Seedable to work properly!**

**Why is this required?**

Seedable needs to know which of your indexers are private vs public to properly filter and label results. **Without this configuration, Seedable's filters will aggressively remove most or all search results**, leaving you with few or no torrents to download.

**How Seedable works with Private + Public trackers:**

Seedable is designed to work with **BOTH private and public trackers** simultaneously. The `PRIVATE_TRACKERS` setting tells Seedable:
1. Which trackers are private (so it can label them correctly)
2. How to prioritize results for maximum cross-seeding potential

**Configuration Steps:**

1. **Find your tracker names in NZBHydra2:**
   - Go to **Config** → **Indexers**
   - Look at the **Name** column
   - Copy the exact names of your **PRIVATE trackers only**

2. **Add them to your .env file:**

```bash
# Example with private trackers:
PRIVATE_TRACKERS=TorrentLeech,IPTorrents,PassThePopcorn,BroadcasTheNet

# Example with different private trackers:
PRIVATE_TRACKERS=PrivateHD,HDTorrents,AlphaRatio,MyTracker,TorrentVault
```

**⚠️ Use exact names from NZBHydra2 - Case sensitive! Comma-separated, no spaces!**

**What happens with this configuration:**

✅ **With PRIVATE_TRACKERS set:**
- Seedable labels all results: `[PRI:2 PUB:1] Movie.Title.1080p`
- Filters to show torrents that exist on 2+ trackers where at least 1 is private
- You can download from public trackers knowing you can cross-seed to private trackers
- Maximizes your upload ratio on private trackers

❌ **Without PRIVATE_TRACKERS set (or set incorrectly):**
- Seedable cannot distinguish private from public trackers
- Filtering becomes too aggressive
- Most/all results get filtered out
- **You will get few or no search results!**

**Result Labels:**

When properly configured, torrents show labels at the front for easy sorting:
- `[PRI:2 PUB:1] The.Matrix.1999.1080p.AMZN.WEB-DL` - 2 private trackers, 1 public tracker ← **Best for ratio!**
- `[PRI:3 PUB:0] Interstellar.2014.2160p.BluRay` - Private-only (3 private trackers)
- `[PRI:1 PUB:2] Avatar.2009.1080p.BluRay` - 1 private tracker, 2 public trackers

**Can I use only public trackers?**

Yes! If you **only** have public trackers (no private), you can leave `PRIVATE_TRACKERS` empty:

```bash
PRIVATE_TRACKERS=
```

In this case:
- All results show as `[PUB:X]` with no PRI label
- Seedable filters to show torrents on 2+ public trackers
- Works perfectly for public-only setups

**Summary:**
- **Private trackers only:** Set `PRIVATE_TRACKERS` to your private tracker names
- **Public + Private (recommended):** Set `PRIVATE_TRACKERS` to your private tracker names
- **Public trackers only:** Leave `PRIVATE_TRACKERS` empty

**This setting is the difference between Seedable working perfectly and not working at all!**

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

**This is the #1 most common issue!** You didn't select ALL categories (main + subcategories).

**Solution:**
1. Go to Sonarr/Radarr → **Settings** → **Indexers**
2. Edit the Seedable indexer
3. **Select ALL categories** - not just the main one, not just subcategories, but **ALL of them**:
   - **Sonarr:** Check **5000 (TV)** AND **5020, 5030, 5040, 5045, 5050, 5060, 5070, 5080**
   - **Radarr:** Check **2000 (Movies)** AND **2010, 2020, 2030, 2040, 2045, 2050, 2060**
4. Save and test again

**Why ALL categories?** Different indexers assign the same torrent to different categories:
- Some indexers use the main category (5000 or 2000) for everything
- Others use specific subcategories (5040 for TV HD, 2045 for Movies UHD)
- The SAME torrent might be in category 5000 on one indexer and 5045 on another
- If you don't select all categories, you'll miss results

**Example:** "The Matrix 1080p" might be:
- Category 2000 (Movies) on IndexerA
- Category 2040 (Movies HD) on IndexerB
- Category 2045 (Movies UHD) on IndexerC

If you only select 2000, you'll miss the results from IndexerB and IndexerC!

### No results in Sonarr/Radarr

**Possible causes (in order of likelihood):**

**1. Missing PRIVATE_TRACKERS configuration (MOST COMMON!)**

If you have private trackers but didn't configure `PRIVATE_TRACKERS` in your `.env` file, Seedable will filter out most/all results!

**Solution:**
```bash
nano /opt/seedable/.env
```
Add your private tracker names:
```bash
PRIVATE_TRACKERS=TorrentLeech,IPTorrents,YourPrivateTracker
```
Then restart:
```bash
docker-compose restart seedable
```

**2. Didn't select all categories**

See the section above: "Query successful, but no results in the configured categories"

**3. Check Seedable logs:**
```bash
docker logs seedable
```

Look for lines like:
```
Category filtered to 0 results matching ['5030', '5040', '5070']
```
If you see this, you forgot categories (see solution above)!

Look for lines like:
```
Filtered to 0 cross-seedable results (min 2 trackers)
```
If you see this, check your `PRIVATE_TRACKERS` setting!

**4. Verify NZBHydra2 is accessible:**
```bash
curl http://YOUR_SERVER_IP:5076/internalapi/search \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"test","category":"All"}'
```

**5. Lower MIN_DUPLICATES temporarily for testing:**
Edit `.env`:
```bash
MIN_DUPLICATES=1  # Shows all results (no filtering)
```
Then: `docker-compose restart seedable`

### Too few results

- Lower `MIN_DUPLICATES` to 2 (if set higher)
- Increase `SIZE_TOLERANCE_PERCENT` to 3-5%
- Check that NZBHydra2 has multiple indexers configured

### API key errors

Make sure the API key in Sonarr/Radarr matches the `API_KEY` in your `.env` file.

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
