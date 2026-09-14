# Tennessee Bound — Deployment Guide

## Site Structure
```
site/
├── index.html          ← Main landing page
├── covers/
│   ├── vol1-3d.png     ← 3D mockup (hero fan)
│   ├── vol2-3d.png
│   ├── vol3-3d.png
│   ├── vol1-tax-ledger-flat.png   ← Flat cover (book cards)
│   ├── vol2-town-ledger-flat.png
│   └── vol3-landing-ledger-flat.png
└── qr/
    ├── tennessee-bound-qr.svg
    ├── tennessee-bound-qr-navy.png
    ├── tennessee-bound-qr-navy-transparent.png
    └── tennessee-bound-qr-print.png
```

## Deploying to Cloudflare Pages (Direct Upload)

1. Zip the `site/` folder contents (not the folder itself):
   ```
   cd site && zip -r ../tennessee-bound-site.zip . && cd ..
   ```
2. Go to https://dash.cloudflare.com → Pages → your project
3. Upload the zip via **Direct Upload**
4. Connect custom domain `tennesseebound.it.com` in Cloudflare DNS settings

## Wiring Gumroad Products

1. Create products on https://gumroad.com/dashboard
2. Copy each product's share URL (e.g., `https://yourusername.gumroad.com/l/abc123`)
3. Edit `index.html` and fill in the `GUMROAD_LINKS` object:
   ```javascript
   const GUMROAD_LINKS = {
     vol1:   "https://yourusername.gumroad.com/l/vol1-link",
     vol2:   "https://yourusername.gumroad.com/l/vol2-link",
     vol3:   "https://yourusername.gumroad.com/l/vol3-link",
     bundle: "https://yourusername.gumroad.com/l/bundle-link",
     free:   "https://yourusername.gumroad.com/l/free-sample"
   };
   ```
4. Re-deploy to Cloudflare

## Before Launch Checklist
- [ ] Replace SAMPLE testimonials with real reader reviews
- [ ] Fill in Gumroad product links
- [ ] Set up `privacy@tennesseebound.it.com` email
- [ ] Test-buy one product to confirm PDF delivery
- [ ] Connect custom domain in Cloudflare
