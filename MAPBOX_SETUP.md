# 🗺️ Mapbox Setup Guide

## Get Your Free Mapbox Token

Your map is now powered by Mapbox! To make it work, you need a free Mapbox access token.

### Step 1: Create a Mapbox Account (FREE)

1. Go to: **https://account.mapbox.com/auth/signup/**
2. Sign up for a free account (no credit card required!)
3. Confirm your email

### Step 2: Get Your Access Token

1. After logging in, go to: **https://account.mapbox.com/access-tokens/**
2. Copy your **"Default public token"** (it starts with `pk.`)
3. Or create a new token by clicking **"Create a token"**

### Step 3: Add Token to Your App

#### Option A: Environment Variable (Recommended for Production)

1. Go to your Vercel Dashboard: https://vercel.com/dashboard
2. Select your project: **5g-availability-checker**
3. Go to **Settings** → **Environment Variables**
4. Add new variable:
   - **Name**: `MAPBOX_TOKEN`
   - **Value**: Your token (paste it here)
5. Click **Save**
6. Redeploy your app

Then update `templates/map.html` line 318:
```javascript
mapboxgl.accessToken = '{{ MAPBOX_TOKEN }}';
```

#### Option B: Direct Replacement (Quick Test)

1. Open `templates/map.html`
2. Find line 318:
   ```javascript
   mapboxgl.accessToken = 'pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjbGV4YW1wbGUifQ.example';
   ```
3. Replace with your actual token:
   ```javascript
   mapboxgl.accessToken = 'pk.YOUR_ACTUAL_TOKEN_HERE';
   ```
4. Save and redeploy

## Features You Get with Mapbox

✨ **Beautiful Map Styles**:
- Light theme: Modern streets style
- Dark theme: Sleek dark style

🎮 **Interactive Controls**:
- Navigation (zoom, rotate, tilt)
- Fullscreen mode
- Scale indicator

🚀 **Performance**:
- Vector tiles (super fast)
- Smooth animations
- 3D capabilities

📊 **Free Tier Limits**:
- 50,000 map loads per month (FREE!)
- 100 GB map tile requests
- Perfect for your 5G checker app!

## Mapbox Styles Available

You can change the map style by editing line 355-356 in `map.html`:

```javascript
// Current styles:
Light: 'mapbox://styles/mapbox/streets-v12'
Dark: 'mapbox://styles/mapbox/dark-v11'

// Other beautiful styles you can try:
Satellite: 'mapbox://styles/mapbox/satellite-streets-v12'
Outdoors: 'mapbox://styles/mapbox/outdoors-v12'
Light (minimal): 'mapbox://styles/mapbox/light-v11'
```

## Need Help?

- **Mapbox Docs**: https://docs.mapbox.com/
- **Token Management**: https://account.mapbox.com/access-tokens/
- **Pricing**: https://www.mapbox.com/pricing (Free tier is generous!)

---

**Note**: Without a valid token, you'll see a "Token is required" error. Just follow the steps above to fix it! 🎯

